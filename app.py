import pickle
from pathlib import Path
import requests
import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth



# User Authentication
names = ["a","b", "c"]
usernames = ["a","b", "c"]

#load hashed passwords
file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

st.image("/Users/mansidabriwal/Desktop/Hackathon/therapy.jpeg")


authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
    'some_cookie_name', 'some_signature_key', cookie_expiry_days=30)

name, authentication_status, username = authenticator.login('Login', 'main')

# If authentication is  successful show the main page else display login page again
if authentication_status:
    # List of clients
    client_data = "Client_Data.csv"
    df = pd.read_csv(client_data)
    clients = df['Client Name'].tolist()

    # Logout 
    def logout():
        authenticator.logout('Logout', 'main')

    def main():
        
        st.title("SessionSync AI")
        st.sidebar.title('Welcome *%s*' % (name))

        # Displays all the clients
        selected_client = st.sidebar.selectbox("Select a client", clients)
        
        st.sidebar.button("Logout", on_click= logout)

        #Chat history for all the clients
        chat_history_key = f"chat_history_{selected_client}"
        if chat_history_key not in st.session_state:
            st.session_state[chat_history_key] = []
        client_no = 0
        for i in range(0,2):
            if df['Client Name'][i] == f"{selected_client}":
                client_no = df['Client_ID'][i]

        #ChatBot input
        prompt = st.chat_input(f"Ask anything about {selected_client}!")
   
        #Gives answer to the entered input and also suggests questions
        def text_que(prompt):
            if prompt:
                st.session_state[chat_history_key].append({'role': 'user', 'message': prompt})
                response = requests.get(f"http://0.0.0.0:8000/replies/?question={prompt}&client={client_no}")
                reply = response.json()
                bot_response = reply
                #Question and answers and stored in a chat history 
                st.session_state[chat_history_key].append({'role': 'bot', 'message': bot_response})
                
                #Question suggestions, according to the previous question
                response = requests.get(f"http://0.0.0.0:8000/suggestions/?suggested_question={prompt}&client={client_no}")
                question = response.json()
                questions_list = question.split("?")
                questions_list = [question if question.endswith("?") else question + "?" for question in questions_list[:-1]] + [questions_list[-1]]

        
                #Displays 3 questions for suggestion 
                st.button(questions_list[0], on_click=lambda: text_que(questions_list[0]) )
                st.button(questions_list[1], on_click=lambda: text_que(questions_list[1]) )
                st.button(questions_list[2], on_click=lambda: text_que(questions_list[2]) )
                                
                st.session_state[prompt] = ""

        text_que(prompt)
        #Displaying Chat History of conversation between user and Bot
        for chat in st.session_state[chat_history_key]:
            with st.container():
                if chat['role'] == 'user':
                    with st.chat_message("user"):
                        st.write(f"{chat['message']}")
                else:
                    with st.chat_message("assistant"):
                        st.write(f"{chat['message']}")
        
        def reset_conversation():
            st.session_state[chat_history_key] = []
        
        #Button to clear all the messages from the chat window
        st.button('Reset Chat', on_click=reset_conversation)
       

    if __name__ == "__main__":
        main()

#If user authentication fails
elif authentication_status == False:
    st.error('Username/password is incorrect')

#If username or password is missing
elif authentication_status == None:
    st.warning('Please enter your username and password')
