import re
import openai
import streamlit as st
from supabase import create_client

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def write_prompt_result(prompt, result):
    data = supabase.table("python quiz")\
        .insert({"prompt": prompt, "results": result})\
        .execute()
    print(data)

supabase = init_connection()

openai.api_key = st.secrets.OPENAI_TOKEN
openai_model_version = "gpt-3.5-turbo"

col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    st.image('./data/python.png', width=100)
with col2:
    st.markdown("<h1 style='text-align: center;'>Python Quiz</h1>", unsafe_allow_html=True)
with col3:
    st.image('./data/python.png', width=100)

st.markdown("<div style='text-align: center;'><h3>AI와 함께 당신의 파이썬 실력을 업그레이드하세요!</h3></div>", unsafe_allow_html=True)
st.markdown("<div style='text-align: right;'>(Powered by gpt-3.5-turbo)</div>", unsafe_allow_html=True)
st.write("")

def generate_prompt(difficulty):
    prompt = f"파이썬 학습용 4지선다형 문제를 난이도({difficulty})에 맞춰 1개 내주세요. 다음 형식에 맞 답변을 주세요. 그리고 4개의 보기는 반드시 (1) (2) (3) (4)로 시작해야 합니다.\n\n<문제>\n<보기>\n<정답>\n<해설>"
    return prompt.strip()

def request_chat_completion(prompt):
    response = openai.ChatCompletion.create(
        model=openai_model_version,
        messages=[
            {'role': 'system', 'content': '당신은 유용한 도우미입니다.'},
            {'role': 'user', 'content': prompt}]
    )
    return response['choices'][0]['message']['content']

def parse_question(answer):
    lines = answer.split("\n")
    question = lines[1].strip()
    choices_start = 3
    choices_end = lines.index("<정답>")
    choices_lines = lines[choices_start:choices_end]
    choices = []

    for line in choices_lines:
        match = re.match(r"\((\d+)\) (.*)", line.strip())
        if match:
            choice_number = match.group(1)
            choice_text = match.group(2)
            choices.append((choice_number, choice_text))

    correct_answer = re.match(r"\((\d+)\)", lines[choices_end + 1].strip()).group(1)
    explanation = lines[-1].strip()
    return question, choices, correct_answer, explanation

difficulty = st.selectbox("난이도 선택", ["상", "중", "하"], key="difficulty_key")
st.write("")

if 'new_question' not in st.session_state:
    st.session_state.new_question = False
if 'not_selected_yet' not in st.session_state:
    st.session_state.not_selected_yet = True
if 'question' not in st.session_state:
    st.session_state.question = ""
if 'choices' not in st.session_state:
    st.session_state.choices = []

# 버튼을 누를 때
if st.button("문제를 주세요", key="new_question_button"):
    prompt = generate_prompt(difficulty)

    with st.spinner('AI가 문제를 출제 중입니다'):
        answer = request_chat_completion(prompt)
        write_prompt_result(prompt, answer)
        question, choices, correct_answer, explanation = parse_question(answer)

    st.session_state.choices = [f"{choice[0]}. {choice[1]}" for choice in choices]
    st.session_state.correct_answer = correct_answer
    st.session_state.explanation = explanation
    st.session_state.question = question
    st.session_state.not_selected_yet = True

if st.session_state.question:
    st.write(f"문제: {st.session_state.question}")

    if st.session_state.choices:
        response = st.radio("", tuple(st.session_state.choices), key="radio_choice")
        selected_choice = response.split('.')[0] if response else ""

        if st.button("제출", key="submit_button"):
            st.write(f"선택한 답: {selected_choice}")

            if selected_choice == st.session_state.correct_answer:
                st.success("정답입니다!")
            else:
                st.warning("오답입니다.")
            st.write(f"정답: {st.session_state.correct_answer}")
            st.write(f"해설: {st.session_state.explanation}")

            st.session_state.not_selected_yet = False