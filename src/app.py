import streamlit as st
from main_loop import evaluate_prompt
from config import LOOP_COUNT
from PIL import Image


st.set_page_config(page_title="Agent Eval", page_icon="🤖", layout="centered")
st.title("Agent Eval")


# Open the image file
image = Image.open("src/images/agent_logo.png")
image = image.resize((300, 300))

# Display the image
col1, col2, col3 = st.columns([1, 2, 1])  # middle column is wider
with col2:
    st.image(image, caption="LLM Babysitter", use_container_width=False)


prompt = st.text_area("Enter your prompt:")

if st.button("Start Streaming"):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Action Agent")
        container1 = st.container()

    with col2:
        st.subheader("Evaluation Agent")
        container2 = st.container()

    gen = evaluate_prompt(prompt)

    # Loop until generator is exhausted - it will alternate between agents
    for i in range(LOOP_COUNT):
        try:
            msg1 = next(gen)
            container1.write(msg1)  # append, does not overwrite
        except StopIteration:
            break

        try:
            msg2 = next(gen)
            container2.write(msg2)
        except StopIteration:
            break

        if gen is None:
            break

    if i == LOOP_COUNT-1:
        container1.write("API CALL LIMIT REACHED")
