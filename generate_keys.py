import pickle
from pathlib import Path

import streamlit_authenticator as stauth

names = ["a","b", "c"]
usernames = ["a","b", "c"]
passwords = ["XXXX", "XXXX", "XXXX"]

hashed_password = stauth.Hasher(passwords).generate()

# Saves the hashed passwords to a file 
file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("wb") as file:
    pickle.dump(hashed_password, file)
#This will create the binary file and  stores hashed passwords in it.