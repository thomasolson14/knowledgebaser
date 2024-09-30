#llm_api.py
import openai
from openai import OpenAI
import time
import ast

##LLM API - interface with openAI
class llmAPI():
    def __init__(self):
        #run - export OPENAI_API_KEY="your open api key" - in terminal
        self.client = OpenAI()

    def prettify(self, text):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Correct the grammar. Respond with only the corrected version of the user input"},
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": "The corrected text is:"}
              ]
            )
            # Extract the corrected text
            pretty_text = response.choices[0].message.content.strip()
            return pretty_text
        except Exception as e:
            print(f"Failed to get response: {e}")
            raise e

    def generate_keywords(self, text):
        print("GEN KEYWORDS")
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"The following text is from a Help Guide. Generate keywords a user may search that this Help Guide directly answers. Respond with only an array containing each keyword.\nHelp Guide:\n"},
                    {"role": "user", "content": text}
              ]
            )
               
            keywords = ast.literal_eval(response.choices[0].message.content.strip())
            return keywords

        except Exception as e:
            print(f"Failed to get response: {e}")
            raise e

    def generate_potential_questions(self, text):
        print("GEN Qs")
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"The following text is from a Help Guide. Generate all simple questions a user may ask that this Help Guide directly answers. Respond with only an array containing each sentence.\nHelp Guide:\n"},
                    {"role": "user", "content": text}
              ]
            )
            response_text = response.choices[0].message.content.strip()
               
            questions = ast.literal_eval(response.choices[0].message.content.strip())

            validation = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"The following text is from a Help Guide. Generate all simple questions a user may ask that this Help Guide directly answers. Respond with only an array containing each sentence.\nHelp Guide:\n"},
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": response_text},
                    {"role": "user", "content": "Do these questions accurately cover the content of the article? True or False."}
              ]
            )
            if 'true' in validation.choices[0].message.content.lower():
                return questions
            else:
                raise Exception("validation failed")
        except Exception as e:
            print(f"Failed to get response: {e}")
            raise e

    def get_embedding(self, text):
        text = text.replace("\n", " ")
        return self.client.embeddings.create(input = [text], model="text-embedding-3-small").data[0].embedding

    #check groundedness and if answer is possible, return relevance score.
    def evaluate_relevance(self, question, text):
        print(f"GEN EVAL: {question}")
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Using no other information than the given Source Text, can you answer the given Question? Respond with only True or False\n"},
                    {"role": "assistant", "content": "Source Text: "},
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": "Question: "},
                    {"role": "user", "content": question},
                    {"role": "user", "content": "Using no other information than the Source Text, do you have the information needed to answer the Question? True or False."}
              ]
            )
            # Extract the corrected text
            is_relevant = 'true' in response.choices[0].message.content.lower()

            if not is_relevant:
                return 0

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Using no other information than the given Source Text, can you answer the given Question? Respond with only True or False\n"},
                    {"role": "assistant", "content": "Source Text: "},
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": "Question: "},
                    {"role": "user", "content": question},
                    {"role": "user", "content": "Using no other information than the Source Text, do you have the information needed to answer the Question? True or False."},
                    {"role": "assistant", "content": "True"},
                    {"role": "user", "content": "Score how relevant the Source Text is to the Question on a scale of [0 - 10].\n The Score will be 0 if the Source Text is not relevant to the question. The Score will be 10 if it perfectly answers the question.\nScore will be closer to 0 if the Source Text contains irrelevant information or not enough information to answer the quesion\n"},
                    {"role": "user", "content": "Respond with only the Score, an integer [0 - 10]"}
              ]
            )
            # Extract the corrected text
            print(response.choices[0].message.content.strip())
            relavancy_score = int(response.choices[0].message.content.strip())
            return relavancy_score

        except Exception as e:
            print(f"Failed to get response: {e}")
            raise e

    #Answer user query with context given by vector db
    def answer_query(self, query, topic, highlight):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "The following text is from a Help Guide. Use only the user provided content to answer the Final Question.\nHelp Guide:\n"},
                    {"role": "user", "content": topic},
                    {"role": "user", "content": "\n The following highlight provides content that may be relevant in answering the Final Question.\nHighlight:\n"},
                    {"role": "user", "content": highlight},
                    {"role": "user", "content": "\nThe following line is the Final Question. Do not answer yet. Using the user provided content, can you answer the question? Respond with only True or False\n"},
                    {"role": "user", "content": f"The Question: {query}\n"},
                    {"role": "user", "content": "True or False?"},

              ]
            )
            can_answer = response.choices[0].message.content.strip().lower()
            if 'true' in can_answer:
                response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "The following text is from a Help Guide. Use only the user provided content to answer the Final Question.\nHelp Guide:\n"},
                    {"role": "user", "content": topic},
                    {"role": "user", "content": "\n The following highlight provides content that may be relevant in answering the Final Question.\nHighlight:\n"},
                    {"role": "user", "content": highlight},
                    {"role": "user", "content": "\nThe following line is the Final Question. Do not answer yet. Using the user provided content, can you answer the question? Respond with only True or False\n"},
                    {"role": "user", "content": f"The Question: {query}\n"},
                    {"role": "assistant", "content": "True"},
                    {"role": "user", "content": "Answer the Final Question, using exact text from the above excepts to answer the question as much as possible.\n\n"},
                    {"role": "user", "content": query},
              ]
            )
                answer = response.choices[0].message.content.strip()
                return answer
            else: 
                return None
        except Exception as e:
            print(f"Failed to get response: {e}")
            raise e

    #answer with context of matching keywords
    def answer_if_possible(self, query, context_text):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "The following text is from a Help Guide. Use only the user provided content to answer the Final Question.\nHelp Guide:\n"},
                    {"role": "user", "content": context_text},
                    {"role": "user", "content": "\nThe following line is the Final Question. Do not answer yet. Using the user provided content, can you answer the question? Respond with only True or False\n"},
                    {"role": "user", "content": f"The Question: {query}\n"},
                    {"role": "user", "content": "True or False?"},
              ]
            )
            can_answer = response.choices[0].message.content.strip().lower()
            if 'true' in can_answer:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "The following text is from a Help Guide. Use only the user provided content to answer the Final Question.\nHelp Guide:\n"},
                        {"role": "user", "content": context_text},
                        {"role": "user", "content": "\nThe following line is the Final Question. Do not answer yet. Using the user provided content, can you answer the question? Respond with only True or False\n"},
                        {"role": "user", "content": f"The Question: {query}\n"},
                        {"role": "assistant", "content": "True"},
                        {"role": "user", "content": "Answer the Final Question, using exact text from the above excepts to answer the question as much as possible.\n\n"},
                        {"role": "user", "content": query},
                    ]
                )
                answer = response.choices[0].message.content.strip()
                return answer
            else: 
                return None
        except Exception as e:
            print(f"Failed to get response: {e}")
            raise e
