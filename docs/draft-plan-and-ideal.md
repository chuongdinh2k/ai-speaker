Phase 1: 
Description for this phase: 
An app help users to login and chat with botAI with vary topics, bot can answer with text or voice, memory chat history, user delete conversations
Features:

- login
- user choose topic ⇒ chat with AI
- AI can read context of history chat
- With a single topic will have specific prompts ⇒ can edit or added
- Allow send voice or text or both
- Delete conversation

Technical should use: 

- Backend: Python Fastify for API
- Langchain, RAG
- Web socket
- Frontend: React, Taiwind
- Database: Postgres vector
- Redis: Queues
- OpenAI

Flow for start a conversation: 
- choose conversation with topic ( store topic is unique row combine with (userId, topicId) ) ⇒ server create new conversation info ⇒ load compatible prompts ⇒ load user history

Flow delete a conversation:
- delete all messages and relative conversation

Flow choose include send voice or not or both:
- user can choose send and reploy with voice from user and both

Flow for chat: 
- send messages ⇒ chat LLM call to OpenAI ( load history too ) ⇒ response socket to user

Database: 
- user info
- prompt_templates
- conversations
- messages
- topics
- subcription

Out of scope ( but should  be included in phase 2 ):
- ranking user
- user credit
- chat mode ( friends, professional )
- contributor can question and answer ( specific topic ) knowledge bases

Non-functional: 
- response should fast and accurate as well as possible
- cost save
- architecture should extend in future ( as microservices architecture )