import streamlit as st
from streamlit_extras.colored_header import colored_header

from pyairtable import Table

import openai


# Config page
st.set_page_config(
    page_title="Spiritus",
    page_icon="⚙️",
    layout="centered"
)

##########
# Title
colored_header(
    label="Spiritus",
    description="For fast interactions about the chatbot development",
    color_name="blue-green-70",
)

# Set OpenAI API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]
airtable_api_key = st.secrets["AIRTABLE_API_KEY"]

base_id = "appfP79bOaVRUgYct"
table_id = "tblRlqxZMacjfjwKD"
at_prompt = Table(airtable_api_key, base_id, table_id)
at_prompt_records = at_prompt.all()

for at_prompt_record in at_prompt_records:
    if "active_prompt_system" in at_prompt_record["fields"]:
        if at_prompt_record["fields"]["active_prompt_system"]:
            prompt_system = at_prompt_record["fields"]["prompt"]

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": prompt_system
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Pose moi une question…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        for response in openai.ChatCompletion.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
            temperature=1
        ):
            full_response += response.choices[0].delta.get("content", "")
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})

