# RAG-Based-User-Content-Summariser

## Abstract
User-generated content (UGC) platforms are key sources for tasks ranging from product recommendations to technical problem-solving. However, users often encounter scattered, disorganized, and sometimes contradictory information. To address this, we propose the RAG-Based User Content Summarizer (RBUCS), a system designed to aggregate and distill UGC into coherent responses.

RBUCS leverages Retrieval-Augmented Generation (RAG) with Large Language Model (LLM). Upon receiving a user query, the system performs text classification to select the optimal information processing strategy and output template. For recommendation queries, it extracts candidate items, synthesizes user opinions, and outputs ranked recommendations with supporting evidence. For general queries, it generates comprehensive summaries of the most relevant sources. RBUCS employs a hybrid retrieval mechanism, combining vector-based semantic search (FAISS), traditional text matching (BM25), and content quality signals (e.g., user votes/likes) to identify relevant documents across platforms like Reddit, Stack Overflow, and Rednote.

To evaluate the retrieval effectiveness of our RAG module, we labeled 150 query-document samples. Each sample contains a short user query and five relevant Rednote posts. The result shows that our approach achieves 100% Recall@5 and 89.44% Precision@5, suggesting that users, in the Rednote ecosystem, can expect to consistently find all relevant posts within the top results.

Overall, RBUCS effectively streamlines the process of reviewing and analyzing UGC, offering concise and targeted summaries to mitigate information overload on modern UGC platforms.

## Poster
![Coding Fest 2025_RBUCS_page-0001](https://github.com/user-attachments/assets/dd4391c4-95c4-45c0-aa6d-18def2d1d720)

## Demo
Coming soon...

## Contributing
See CONTRIBUTION.md

## Other Resources
- [Web Development](https://www.notion.so/Web-Development-d45066738c604a8cbf783bf8ac1bcae7?pvs=4)
- [Tasks](https://docs.google.com/document/d/1pWmh07-DyQ-Cz5ZIpRNOjjC2DhFShZApeUEzYii5-n4/edit?usp=sharing) (Tentative; used for drafting the product backlog)
