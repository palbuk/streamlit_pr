import streamlit as st
import ollama

model_name = "hf.co/MLP-KTLim/llama-3-Korean-Bllossom-8B-gguf-Q4_K_M:Q4_K_M"

# Streamlit UI 구성
st.title("Ollama 모델과 채팅")
user_input = st.text_input("질문을 입력하세요", "하늘이 파란 이유는?")

if st.button("모델에게 물어보기"):
    if user_input.strip():
        st.write("***모델의 응답:***")
        response_placeholder = st.empty()

        try:
            response_stream = ollama.chat(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": user_input,
                    }
                ],
                stream=True  # 스트리밍
            )

            full_response = ""
            for chunk in response_stream:
                full_response += chunk['message']['content'] # 응답을 계속해서 추가
                response_placeholder.markdown(full_response)
            
            st.success("모델 응답 완료")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

    else:
        st.warning("질문을 입력해주세요.")