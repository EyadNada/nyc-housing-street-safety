# Prompts log

The project rules ask for **all prompts used**. Below is every prompt the team sent to an AI assistant, word for word, with the files attached and what we used the answer for.

**Tool:** Claude (Anthropic), in the Claude app. **Date of all prompts below:** 9 October 2026.

> **Members:** if you use an AI tool for your part (for example to explain code before the evaluation), add your prompt here before the submission deadline.

| # | Prompt (word for word) | Files attached | What we used the answer for |
|---|---|---|---|
| 1 | "Here is everything related to the Data Engineering Project , I want you to analyze the file carefully read everything twice and then after that I want you to tell me what do you need from as course material for example or anything else before you start working , make sure that I want a  full grade on this project as it represents a large sum from the grades of the subject , also we are 6 members in the team so divide the work as you are moving on through the project so that every member know what to memorize as there is evaluation I think which is graded." | Project Description.pdf, Data Catalog.pdf | Checklist of deliverables and grading criteria; first team-role split; timeline |
| 2 | "I will upload to you the course materials right now so that you can start working but as for milestone 2 we don't have yet it hasn't been posted till now , and also I will provide you with the names and id's and the GitHub usernames as you want and for the strengths we are all the same so divide it as you like. We didn't choose a dataset yet so you choose for us the easiest" | none | Dataset choice: Affordable Housing Production by Building (H2) + SIRTA (T4), after checking their real columns and sizes |
| 3 | "Here are the lectures wait for the labs . There are a lot of things so I will provide them lab by lab ok ." | Lecture_1.pdf to Lecture_4.pdf | Course terms used in the notebook (ETL, tidy data, data types, IQR rule, chart choice, no pie charts) |
| 4 | "Here is lab 1." | Lab 1 notebook, adult.csv, Report.html, Adult_Sweetviz_Report.html, Adult_Sweetviz_Compare.html | EDA order, hidden missing values check, ydata-profiling and Sweetviz reports |
| 5 | "Wait I forgot these too in Lab 1" | 5 figures from Lab 1 (scraping pipeline, DOM tree, DevTools, tags) | Extract pipeline table in Section 1 |
| 6 | "Here is Lab 2" | Lab 2 notebook and datasets (retail_transactions, placement, heart, stock, Uni_Ranking, Airbnb_Open_Data) | Missing-value and outlier methods, Hot Deck imputation, Plotly maps, Dash callbacks |
| 7 | "Here is Lab 3" | Lab 3 manual, notes, Power BI file, 4 theme files, Links.doc, Remote Work dataset | Dashboard design (KPI cards, filters, safe division), whole-word replacement |
| 8 | "And finally here is Lab 4" | Lab 4 handout and notes | Drill-through, tooltips, ranking measures, merging after aggregation |
| 9 | "This is everything as course materials , you are the mentor here Claude don't ask me what to change just choose the easiest for us and also make sure to choose what gets us the full grade with the bonus if found too that's all we want" | none | Final research questions, integration levels and website plan |
| 10 | "Here you baby girl" | hg8x-zxpr.csv, xeqp-qz8h.csv (downloaded from the API) | Raw data snapshot used by the notebook and website |

## How the answers were checked

- Every number in the notebook text was compared with the output of the code above it. Where they differed, the text was corrected.
- Cleaning methods were tested before use (for example, the ZIP imputation was tested on hidden ZIP codes: 92% and 73% correct).
- The website was tested with automatic tests (`tests/`) and a headless browser.
