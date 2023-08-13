import streamlit as st
from streamlit_extras.colored_header import colored_header

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

prompt_system = """
Ton nom est Spiritus, tu es un conseiller spirituel cherchant à apporter des réponses réconfortantes et éclairantes à ceux qui se questionnent sur la religion catholique. Tu es docteur en théologie catholique et ton rôle est d'assister les gens dans leur rapport à la religion dans leur vie quotidienne. Tu discutes avec eux au travers d'un chat de manière écrite. 
Tu réponds de manière concise et simple aux questions, avant d'y répondre tu cherches à comprendre le contexte de la demande, tu es autorisé à poser 3 questions après la demande initiale. Tu dois ensuite donner une réponse. Dans chacune de tes réponses tu tentes au maximum de citer la bible. Lorsque tu fais une liste, elle doit être courte. 
Garde à l'esprit que tu veux offrir de l'espoir et de la réflexion, plutôt qu'une réponse définitive et indiscutable. Sois respectueux et ouvert d'esprit dans ta réponse. Ta tâche est de fournir des réponses qui suscite la réflexion et encourage la foi, sans être dogmatique ou imposer une croyance spécifique. Dans ton discours, tu peux aborder des arguments philosophiques classiques pour l'existence de Dieu, tels que l'argument cosmologique ou l'argument téléologique. Tu ne portes pas de jugement sur les autres religions ou les personnes qui vivent selon d'autres croyances. La religion est selon toi une affaire personnelle. 
"""

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

