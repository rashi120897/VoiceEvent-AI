# VoiceEvent-AI


VoiceEvent AI | Real-Time AI Voice Concierge

I built VoiceEvent AI to help event guests find information through natural voice conversations. Guests can ask questions about schedules, venues, parking, transportation, and accommodations, with the assistant retrieving relevant event information to guide its responses.

The project combines real-time voice interaction with retrieval-augmented generation (RAG). I developed a retrieval pipeline using LangChain, OpenAI embeddings, and Pinecone to find relevant content from event documents and bring that context into the conversation. This grounds responses in information specific to the event.

I built the backend using Python and FastAPI, integrated Twilio and the OpenAI Realtime API for live speech-to-speech conversations, and used LangGraph to organize conversational workflows. The system supports multiple events and organizers, with event-specific context for guest questions.

My work spans backend development, voice integration, retrieval, and conversation orchestration. The project explores how these components can work together to make event information easier to access through a conversational interface.

Technologies: Python, FastAPI, OpenAI Realtime API, Twilio, LangChain, LangGraph, Pinecone, and RAG.
