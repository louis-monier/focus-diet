 # Importing required packages
import streamlit as st
import streamlit_authenticator as stauth
import openai
import uuid
import time
import pandas as pd
import io
from openai import OpenAI
import fitz
import yaml
from yaml.loader import SafeLoader

st.set_page_config(page_title="FinancePro")

# Get the credentials for login
with open('.streamlit/login.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

# Create the login form in the UI
authenticator.login()

if st.session_state["authentication_status"]:

    # Initialize OpenAI client
    client = OpenAI()

    # Your chosen model
    #MODEL = "gpt-3.5-turbo-1106" # Latest model
    MODEL = "gpt-4-turbo-preview"

    # Initialize session state variables
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "run" not in st.session_state:
        st.session_state.run = {"status": None}

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "retry_error" not in st.session_state:
        st.session_state.retry_error = 0

    # Set up the page
    with st.sidebar:
        st.title("FinancePro")
        st.markdown("#### Louis Monier & Thomas Libs")
        st.divider()
        st.write(f'Welcome *{st.session_state["name"]}*')
        authenticator.logout()
        st.divider()
        

    # Initialize OpenAI assistant
    if "assistant" not in st.session_state:
        openai.api_key = st.secrets["OPENAI_API_KEY"]
        st.session_state.assistant = openai.beta.assistants.retrieve(st.secrets["OPENAI_ASSISTANT"])
        st.session_state.prompt_system = st.session_state.assistant.instructions
        st.session_state.thread = client.beta.threads.create(
            metadata={'session_id': st.session_state.session_id}
        )

    # Text input for user to type their instruction
    user_prompt = st.sidebar.text_area("Type the instructions for the Assistant here:", value=st.session_state.prompt_system, height=200)

    # Button to submit the prompt
    if st.sidebar.button('Submit Instruction'):
        st.session_state.user_instruction = user_prompt  # Save the prompt to session state if needed
        st.sidebar.success("Instruction updated successfully!")
        
        # Display the instruction (or you can use this prompt in your logic as needed)
        st.sidebar.markdown("#### Current Assistant Instructions")
        st.sidebar.write(user_prompt)
        
        st.session_state.assistant = client.beta.assistants.update(
            st.secrets["OPENAI_ASSISTANT"],  
            instructions=st.session_state.user_instruction  # Use the instruction from session state
        )

    st.title("FinancePro")

    # File uploader for PDF
    uploaded_file = st.file_uploader('Upload your PDF file', type="pdf")

    if uploaded_file is not None and "file_processed" not in st.session_state:
        # Determine the file type
        file_type = uploaded_file.type

        try:
            # Read the file into a Pandas DataFrame
            if file_type == "application/pdf":
                # Load PDF file
                pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                text = ""
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    text += page.get_text()
                
                # Here you might want to convert text to a DataFrame
                # This depends highly on the structure of your text and what you're aiming to extract
                # For demonstration, let's say each line in the text is a new row in a single-column DataFrame
                df = pd.DataFrame(text.split('\n'), columns=['Text'])
                pdf_document.close()

            # Convert DataFrame to JSON
            json_str = df.to_json(orient='records', indent=4)
            file_stream = io.BytesIO(json_str.encode())

            # Upload JSON data to OpenAI and store the file ID
            file_response = client.files.create(file=file_stream, purpose='assistants')
            st.session_state.file_id = file_response.id
            #print(st.session_state.file_id)
            st.success("File uploaded successfully to OpenAI!")
            st.session_state.file_processed = True  # Set the flag indicating file has been processed

            # Optional: Display and Download JSON
            #st.text_area("JSON Output", json_str, height=300)
            #st.download_button(label="Download JSON", data=json_str, file_name="converted.json", mime="application/json")
        
        except Exception as e:
            st.error(f"An error occurred: {e}")

    # Display chat messages
    elif hasattr(st.session_state.run, 'status') and st.session_state.run.status == "completed":
        st.session_state.messages = client.beta.threads.messages.list(
            thread_id=st.session_state.thread.id
        )
        for message in reversed(st.session_state.messages.data):
            if message.role in ["user", "assistant"]:
                with st.chat_message(message.role):
                    for content_part in message.content:
                        message_text = content_part.text.value
                        st.markdown(message_text)

    # Chat input and message creation with file ID
    if prompt := st.chat_input("Comment puis-je t'aider?"):
        with st.chat_message('user'):
            st.write(prompt)

        message_data = {
            "thread_id": st.session_state.thread.id,
            "role": "user",
            "content": prompt
        }

        # Include file ID in the request if available
        if "file_id" in st.session_state:
            message_data["file_ids"] = [st.session_state.file_id]

        st.session_state.messages = client.beta.threads.messages.create(**message_data)
        #print(message_data)

        st.session_state.run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread.id,
            assistant_id=st.session_state.assistant.id,
        )
        if st.session_state.retry_error < 3:
            time.sleep(1)
            st.rerun()

    # Handle run status
    if hasattr(st.session_state.run, 'status'):
        if st.session_state.run.status == "running":
            with st.chat_message('assistant'):
                st.write("Thinking ......")
            if st.session_state.retry_error < 3:
                time.sleep(1)
                st.rerun()

        elif st.session_state.run.status == "failed":
            st.session_state.retry_error += 1
            with st.chat_message('assistant'):
                if st.session_state.retry_error < 3:
                    st.write("Run failed, retrying ......")
                    time.sleep(3)
                    st.rerun()
                else:
                    st.error("FAILED: The OpenAI API is currently processing too many requests. Please try again later ......")

        elif st.session_state.run.status != "completed":
            st.session_state.run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread.id,
                run_id=st.session_state.run.id,
            )
            if st.session_state.retry_error < 3:
                time.sleep(3)
                st.rerun()

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')