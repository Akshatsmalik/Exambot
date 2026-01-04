import streamlit as st 
import requests

BACKEND_URL = 'http://127.0.0.1:8000/main'

st.set_page_config(page_title="YouTube Q&A", layout="centered")

st.title('Youtube video Q&A')
st.write('Ask questions about any YouTube video!')

video_url = st.text_input(
    'enter the YouTube video URL here:',
    placeholder='https://www.youtube.com/watch?v=example'
)

if video_url:
    st.video(video_url)

question =st.text_input(
    'enter your questions regarding the video',
    placeholder='What is the main topic of the video?'
)

if st.button('Ask'):
    if not video_url or not question:
        st.error("Please provide both a YouTube video URL and a question.")
    else:
        with st.spinner('Processing your request...'):
            try:
                response = requests.post(
                    BACKEND_URL,
                    json={'video_url': video_url, 
                          'question': question}
                )
                if response.status_code == 200:
                    data = response.json()
                    if 'error' in data:
                        st.error(data['error'])
                    else:
                        st.subheader('Answer:')
                        st.write(data['answer'])
                else:
                    st.error(f"Error: Received status code {response.status_code}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

                