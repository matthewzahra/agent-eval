import streamlit as st
import time
from main_loop import evaluate_prompt

# # Example generator functions (simulate LLM streaming)
# def generate_response1(prompt):
#     for i in range(5):
#         time.sleep(0.5)
#         yield f"Response1 part {i} for '{prompt}'"

# def generate_response2(prompt):
#     for i in range(5):
#         time.sleep(0.7)
#         yield f"Response2 part {i} for '{prompt}'"


st.title("LLM Babysitter")

from PIL import Image

# Open the image file
image = Image.open("image.png")  # replace with your file path
image = image.resize((300, 300))  # width=300px, height=200px

# Display the image
st.image(images/image, caption="LLM Babysitter", use_container_width=False)

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

    # Loop until both generators are exhausted
    while True:
        try:
            msg1 = next(gen)
            container1.write(msg1)  # append, does not overwrite
        except StopIteration:
            gen1 = None

        try:
            msg2 = next(gen)
            container2.write(msg2)
        except StopIteration:
            gen2 = None

        if gen is None:
            break
