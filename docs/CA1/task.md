# Project work, part 1 - Dashboard basics

## General

* All project work in IND320 will result in personal hand-ins and online apps.
    1. A Jupyter Notebook run locally on your computer (later with access to online and local databases).
        - This will be your basic development and documentation platform.
        - Must include a brief description of AI usage.
        - Must include a 300-500-word log describing the compulsory work (including both Jupyter Notebook and Streamlit experience).
        - Must include links to your public GitHub repository and Streamlit app (see below) for the compulsory work.
        - Document headings should be clear and usable for navigation during development.
        - All code blocks must include enough comments to be understandable and reproducible if someone inherits your project.
        - All code blocks must be run before an export to PDF so the messages and plots are shown. In addition, add the .ipynb file to the GitHub repository where you have your Streamlit project.

    2. A Streamlit app running at https://[yourproject].streamlit.app/.
        - This will be an online version of the project, accessing data that has been exported to CSV format (later, also an online database).
        - The code, hosted on GitHub, must include relevant comments from the Jupyter Notebook and further comments regarding Streamlit usage.

- There are four parts in the project work, building on each other and resulting in a final portfolio and app to be presented at the end of the semester.
- Co-operation is applauded, and the use of AI tools is encouraged.

---

### Tasks

#### GitHub and Streamlit.app accounts

-Prepare a GitHub account and create a public repository for your project work. Addresses on streamlit.app must be unique, so include your GitHub username or similar in the repository name. Report the Streamlit address and GitHub repository address in the Jupyter Notebook.
- Log in to share.streamlit.io using your GitHub account.
- Create a minimum working example of a Streamlit app, push it to GitHub, and ensure it works at https://[yourproject].streamlit.app/

#### Jupyter Notebook

- Read the reservoirs.csv file using Pandas (located in D2Dbook/data).
- Rename headers to English and understandable.
- Print its contents in a relevant way.
- Plot each column separately.
- Plot all columns together. Consider how to make this natural, given that the scales are different.
- Remember to fill in the log and AI mentioned in the General section above.

#### Streamlit app

- Create a Streamlit app including:
    - requirements.txt or uv.lock (for package dependencies)
    - Four pages (with dummy headers and test content for now) with separate .py files.
        1. The front/home page should have a sidebar menu with navigation options to the other pages.
        2. On the second page:
            - A table showing the imported data (see below). Use the row-wise LineChartColumn() to display the first month of the data series. There should be one row in the table for each column of the imported data.
        3. On the third page:
            - A plot of the imported data (see below), including header, axis titles and other relevant formatting.
            - A drop-down menu (st.selectbox) choosing any single column in the CSV or all columns together.
            - A selection slider (st.select_slider) to select a subset of the months. The default should be the first month.
    - Data should be read from a local CSV-file (reservoirs.csv), using caching for app speed. In part 2 of the project, we will remove this file and rely on MongoDB instead.

#### Screencast

- 5-minute screencast where you briefly showcase your running app and explain what your code does. 
- Canvas does not permit upload of more than one file in the assignment.
    - If you make a screencast in Panopto, you can share a link to your video and add the link to the Jupyter Notebook or as a submission comment (make sure the file permissions are open for anyone).
    - If you use a different tool for making the screen cast, you can upload your video to the GitHub repo.

---

### Evaluation

- The uploaded PDF, GitHub repository, Streamlit app, and screencast will be assessed according to the recipe above.
    - By one fellow student in peer review.
    - By Liland or Osman.
- TA/Teacher's feedback will be short and instructive regarding points of improvement and fulfilment of requirements.
- Final fulfilment of the course will be based on the four rounds of hand-ins seen as a whole.
