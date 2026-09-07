import streamlit as st
from PyPDF2 import PdfReader
import os
import time

from google import genai
from google.genai import types

import chromadb
from chromadb.config import Settings

from typing import List
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    raise ValueError(
        "Gemini API Key not provided. Please provide a valid GEMINI_API_KEY."
    )

client = genai.Client(api_key=gemini_api_key)


# =========================================================
# CHROMADB SETTINGS
# =========================================================

chroma_settings = Settings(
    persist_directory="chroma_db"
)


# =========================================================
# EXTRACT TEXT FROM PDF
# =========================================================

def get_pdf_text(pdf_docs):

    text = ""

    for pdf in pdf_docs:

        pdf_reader = PdfReader(pdf)

        for page in pdf_reader.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text

    return text


# =========================================================
# SPLIT TEXT INTO CHUNKS
# =========================================================

def split_text(text, max_chunk_size=500):

    words = text.split()

    chunks = []
    chunk = []
    chunk_size = 0

    for word in words:

        if chunk_size + len(word) + 1 > max_chunk_size:

            if chunk:
                chunks.append(" ".join(chunk))

            chunk = []
            chunk_size = 0

        chunk.append(word)
        chunk_size += len(word) + 1

    if chunk:
        chunks.append(" ".join(chunk))

    return chunks


# =========================================================
# GEMINI EMBEDDING FUNCTION
# =========================================================

class GeminiEmbeddingFunction:

    def name(self):
        return "gemini_embedding"

    # -----------------------------------------------------
    # Used when adding PDF documents to ChromaDB
    # -----------------------------------------------------

    def __call__(self, input: List[str]):

        embeddings = []

        for text in input:

            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    title="Custom query"
                )
            )

            embeddings.append(
                result.embeddings[0].values
            )

        return embeddings

    # -----------------------------------------------------
    # Used when searching/querying ChromaDB
    # -----------------------------------------------------

    def embed_query(self, input: List[str]):

        start = time.time()

        embeddings = []

        for text in input:

            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY"
                )
            )

            embeddings.append(
                result.embeddings[0].values
            )

        elapsed = time.time() - start

        print(
            f"Query embedding time: {elapsed:.2f}s"
        )

        return embeddings


# =========================================================
# CREATE CHROMADB COLLECTION
# =========================================================

def create_chroma_db(
    documents: List[str],
    db_name: str
):

    start = time.time()

    chroma_client = chromadb.PersistentClient(
        path=chroma_settings.persist_directory
    )

    # -----------------------------------------------------
    # Delete old collection
    # -----------------------------------------------------

    try:

        chroma_client.delete_collection(
            name=db_name
        )

    except Exception:

        pass

    # -----------------------------------------------------
    # Create new collection
    # -----------------------------------------------------

    db = chroma_client.create_collection(
        name=db_name,
        embedding_function=GeminiEmbeddingFunction()
    )

    # -----------------------------------------------------
    # Add documents
    # -----------------------------------------------------

    for i, doc in enumerate(documents):

        db.add(
            documents=[doc],
            ids=[str(i)]
        )

    elapsed = time.time() - start

    print(
        f"PDF / ChromaDB creation time: {elapsed:.2f}s"
    )

    return db


# =========================================================
# LOAD EXISTING CHROMADB COLLECTION
# =========================================================

@st.cache_resource
def load_chroma_collection(db_name: str):

    start = time.time()

    chroma_client = chromadb.PersistentClient(
        path=chroma_settings.persist_directory
    )

    db = chroma_client.get_collection(
        name=db_name,
        embedding_function=GeminiEmbeddingFunction()
    )

    elapsed = time.time() - start

    print(
        f"ChromaDB collection load time: {elapsed:.2f}s"
    )

    return db


# =========================================================
# GET RELEVANT PASSAGE
# =========================================================

def get_relevant_passage(
    query: str,
    db,
    n_results: int
):

    start = time.time()

    results = db.query(
        query_texts=[query],
        n_results=n_results
    )

    elapsed = time.time() - start

    print(
        f"ChromaDB retrieval time: {elapsed:.2f}s"
    )

    return [
        doc[0]
        for doc in results["documents"]
    ]


# =========================================================
# CREATE RAG PROMPT
# =========================================================

def make_rag_prompt(
    query: str,
    relevant_passage: str
):

    escaped_passage = (
        relevant_passage
        .replace("'", "")
        .replace('"', "")
        .replace("\n", " ")
    )

    prompt = f"""
You are a helpful and informative bot that answers questions
using text from the reference passage included below.

Be sure to respond in a complete sentence and provide a
clear and detailed explanation.

When answering questions about the PDF, use the information
from the provided passage.

QUESTION:
'{query}'

PASSAGE:
'{escaped_passage}'

ANSWER:
"""

    return prompt


# =========================================================
# GENERATE GEMINI ANSWER - STREAMING
# =========================================================

def generate_answer(prompt: str):

    start = time.time()

    try:

        chat = client.chats.create(
            model="gemini-3.5-flash-lite"
        )

        response_stream = chat.send_message_stream(
            message=prompt
        )

        elapsed = time.time() - start

        print(
            f"Gemini first response time: {elapsed:.2f}s"
        )

        return response_stream

    except Exception:

        raise


# =========================================================
# DISPLAY STREAMING ANSWER
# =========================================================

def display_streaming_answer(response_stream):

    answer_placeholder = st.empty()

    full_response = ""

    for chunk in response_stream:

        if chunk.text:

            full_response += chunk.text

            answer_placeholder.markdown(
                full_response
            )

    return full_response


# =========================================================
# MAIN STREAMLIT APPLICATION
# =========================================================

def main():

    st.set_page_config(
        page_title="Chat PDF",
        page_icon="💁"
    )

    db_name = "rag_experiment"


    # =====================================================
    # SIDEBAR
    # =====================================================

    with st.sidebar:

        st.title("Menu:")

        mode = st.radio(
            "Choose Mode:",
            (
                "Chat with PDF",
                "General Chat"
            )
        )

        pdf_docs = st.file_uploader(
            "Upload your PDF Files",
            accept_multiple_files=True,
            type=["pdf"]
        )

        if st.button("Submit & Process"):

            if pdf_docs:

                with st.spinner("Processing PDF..."):

                    try:

                        # -------------------------------------------------
                        # Extract text
                        # -------------------------------------------------

                        raw_text = get_pdf_text(
                            pdf_docs
                        )

                        if not raw_text.strip():

                            st.error(
                                "Could not extract text from the PDF."
                            )

                        else:

                            # -------------------------------------------------
                            # Split text
                            # -------------------------------------------------

                            text_chunks = split_text(
                                raw_text
                            )

                            print(
                                f"Number of chunks: {len(text_chunks)}"
                            )

                            # -------------------------------------------------
                            # Create ChromaDB
                            # -------------------------------------------------

                            create_chroma_db(
                                text_chunks,
                                db_name
                            )

                            # -------------------------------------------------
                            # Clear cached collection
                            #
                            # Important because we created a new collection.
                            # -------------------------------------------------

                            load_chroma_collection.clear()

                            st.success(
                                "PDF processed successfully!"
                            )

                    except Exception as e:

                        st.error(
                            f"PDF Processing Error: {str(e)}"
                        )

            else:

                st.error(
                    "Please upload at least one PDF file."
                )


    # =====================================================
    # PAGE HEADER
    # =====================================================

    if mode == "Chat with PDF":

        st.header(
            "Chat with PDF using Gemini 💁"
        )

    else:

        st.header(
            "General Chat using Gemini 💁"
        )


    # =====================================================
    # USER QUESTION
    # =====================================================

    user_question = st.text_input(
        "Ask a Question",
        key="user_question"
    )


    # =====================================================
    # ASK BUTTON
    # =====================================================

    ask_question = st.button(
        "Ask"
    )


    # =====================================================
    # PROCESS ONLY WHEN ASK BUTTON IS CLICKED
    # =====================================================

    if ask_question and user_question.strip():

        # =================================================
        # CHAT WITH PDF
        # =================================================

        if mode == "Chat with PDF":

            try:

                # -------------------------------------------------
                # Load cached ChromaDB collection
                # -------------------------------------------------

                db = load_chroma_collection(
                    db_name
                )

                # -------------------------------------------------
                # Retrieve relevant passage
                # -------------------------------------------------

                relevant_text = get_relevant_passage(
                    user_question,
                    db,
                    n_results=1
                )

                if relevant_text:

                    # -------------------------------------------------
                    # Create RAG prompt
                    # -------------------------------------------------

                    final_prompt = make_rag_prompt(
                        user_question,
                        "".join(relevant_text)
                    )

                    # -------------------------------------------------
                    # Generate streaming answer
                    # -------------------------------------------------

                    response_stream = generate_answer(
                        final_prompt
                    )

                    # -------------------------------------------------
                    # Display streaming answer
                    # -------------------------------------------------

                    st.write("Reply:")

                    display_streaming_answer(
                        response_stream
                    )

                else:

                    st.write(
                        "No relevant information found "
                        "for the given query."
                    )

            except Exception as e:

                st.error(
                    f"PDF Chat Error: {str(e)}"
                )


        # =================================================
        # GENERAL CHAT
        # =================================================

        else:

            prompt = f"""
You are a helpful and informative bot.
Answer the following question in detail.

Question:
{user_question}

Answer:
"""

            try:

                # -------------------------------------------------
                # Generate streaming answer
                # -------------------------------------------------

                response_stream = generate_answer(
                    prompt
                )

                # -------------------------------------------------
                # Display streaming answer
                # -------------------------------------------------

                st.write("Reply:")

                display_streaming_answer(
                    response_stream
                )

            except Exception as e:

                st.error(
                    f"General Chat Error: {str(e)}"
                )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    main()