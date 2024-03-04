import uvicorn
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import requests
import wget
import re
import os
import gunicorn
import httpx
import json
import time
from typing import List, Tuple
import ast 
import openai    
import pandas as pd  
import tiktoken 
import os 
from scipy import spatial 

app = FastAPI()

# defining Api keys and model configurations
openai.api_key = ""  #add your api
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-3.5-turbo"


# import dataset
embeddings_path = "text_embeddings.csv"
df = pd.read_csv(embeddings_path)
df['embedding'] = df['embedding'].apply(ast.literal_eval)


# search and rank function 
def strings_ranked_by_relatedness(
    query: str,
    df: pd.DataFrame,
    relatedness_fn=lambda x, y: 1 - spatial.distance.cosine(x, y),
    top_n: int = 100
) -> Tuple[List[str], List[float]]:
    """Returns a list of strings and relatednesses, sorted from most related to least."""
    query_embedding_response = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=query,
    )
    query_embedding = query_embedding_response['data'][0]['embedding']
    strings_and_relatednesses = [
        (row["text"], relatedness_fn(query_embedding, row["embedding"]))
        for _, row in df.iterrows()
    ]
    strings_and_relatednesses.sort(key=lambda x: x[1], reverse=True)
    strings, relatednesses = zip(*strings_and_relatednesses)
    return list(strings)[:top_n], list(relatednesses)[:top_n]
        
client = openai

def num_tokens(text: str, model: str = GPT_MODEL) -> int:
    """Return the number of tokens in a string."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def query_message(
    query: str,
    df: pd.DataFrame,
    model: str,
    token_budget: int,
    client_number: int 
) -> str:
    """Return a message for GPT, with relevant source texts pulled from a dataframe."""
    
    df = df.iloc[[client_number - 1]]  # Subtract 1 because index starts at 0
    
    strings, relatednesses = strings_ranked_by_relatedness(query, df)
    introduction = 'Use the above transcript which is a therapy session between thearapist and a client to answer the subsequent question. keep the answer crisp. If the answer cannot be found in the articles, write "I could not find an answer."'
    question = f"\n\nQuestion: {query}"
    message = introduction
    for string in strings:
        next_article = f'\n\nTherapy Session History:\n"""\n{string}\n"""'
        if (
            num_tokens(message + next_article + question, model=model)
            > token_budget
        ):
            break
        else:
            message += next_article
    return message + question

#function to ask a question from the given context
def ask(
    query: str,
    df: pd.DataFrame,
    client_number: int,
    model: str = 'gpt-4',
    token_budget: int = 4096 - 500,
    print_message: bool = False,
) -> str:
    """Answers a query using GPT and a dataframe of relevant texts and embeddings."""
    message = query_message(query, df, model=model, token_budget=token_budget, client_number=client_number)
    if print_message:
        print(message)
    messages = [
        {"role": "system", "content": "You answer questions about the therapy session history."},
        {"role": "user", "content": message},
    ]
    
    # Use the correct method for chat completion
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0
    )
    
    response_message = response['choices'][0]['message']['content']
    return response_message

def generate_related_questions(
    query: str,
    df: pd.DataFrame,
    client_number: int,
    model: str = 'gpt-4',
    token_budget: int = 4096 - 500,
    num_questions: int = 3,  # How many related questions you want to generate
    print_message: bool = False,
) -> str:
    """
    Generates a set of questions related to a given query using GPT and a dataframe of relevant texts.
    """
    message = query_message(query, df, model=model, token_budget=token_budget, client_number=client_number)
    
    if print_message:
        print(message)
        
    prompt_to_generate_questions = f"{message}\n\nCan you generate {num_questions} related questions based on the above question and therapy session history?"
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Please generate related questions based on the therapy session history."},
        {"role": "user", "content": prompt_to_generate_questions},
    ]
    
    response = client.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=token_budget
    )
    
    generated_questions = response['choices'][0]['message']['content']
    
    return generated_questions


# api for getting answer when a question is asked
@app.get("/replies/")
def replies(question: str, client: int):
    answer = ask(
        query=question,
        df=df, 
        client_number=client, 
        model="gpt-4",  
)

    return answer


# api for getting questions as suggestion
@app.get("/suggestions/")
def suggestions(suggested_question: str, client: int):
    suggest = generate_related_questions(suggested_question, df, client_number=client)
    print(suggest)
    return suggest

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)