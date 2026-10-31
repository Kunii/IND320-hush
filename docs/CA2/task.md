# Project work, part 2 - Data Sources

## General

* If you push new updates to the main branch of your GitHub repository before the peer review and teacher feedback, things will get cluttered.
    * Create and use a new branch in the GitHub repository for new updates.
    * When peer review and feedback are finished, merge your changes into the main branch.

* All project work in IND320 will result in personal hand-ins and online apps.
    1. A Jupyter Notebook run locally on your computer.
        * This will be your basic development and documentation platform.
            * Must include a brief description of AI usage.
            * Must include a 300-500-word log describing the compulsory work (including both Jupyter Notebook and Streamlit experience).
            * Must include links to your public GitHub repository and Streamlit app (see below) for the compulsory work.
        * Document headings should be clear and usable for navigation during development.
        * All code blocks must include enough comments to be understandable and reproducible if someone inherits your project.
        * All code blocks must be run before an export to PDF so the messages and plots are shown. In addition, add the .ipynb file to the GitHub repository where you have your Streamlit project.

    2. A Streamlit app running at https://[yourproject].streamlit.app/.
        * This is an online version of the project, accessing your MongoDB database for data.
        * The code, hosted on GitHub, must include relevant comments from the Jupyter Notebook and further comments regarding Streamlit usage.

* There are four parts in the project work, building on each other and resulting in a final portfolio and app to be presented at the end of the semester.
* Co-operation is applauded, and the use of AI tools is encouraged.

---

### Tasks

#### Accounts and repositories

* Reuse your account, repository and Streamlit app from the previous part of the project work.
* Until peer review and feedback have been completed, push to a temporary GitHub branch for later merging.

#### Local database: Cassandra

* If not already done, set up Cassandra and Spark as described in the book.
* Test that your Spark-Cassandra connection works.
* The Cassandra database will be accessed from the Jupyter Notebook and used to store data from the APIs mentioned later. 

#### Remote database: MongoDB

* If not already done, prepare a MongoDB account at mongodb.com.
* Test that you can manipulate data from Python.
* The MongoDB database will store data that has been trimmed/curated/prepared through the Jupyter Notebook and Spark filtering.
* These data will be accessed directly from the Streamlit app.

#### API

* Familiarise yourself with the API at Magasinstatistikk API and the descriptions at NVE Magasinstatistikk
    * Remember your experiences regarding the time columns from part 1 of the project.
    * Identify the areas of Norway covered by the different API.
* Familiarise yourself with the API in the ENTSO-E API reference and its account handling and graphical user interface at ENTSO-E
    * Create an account and obtain a security token.

#### Jupyter Notebook

* Remove your CSV-file for the Magasinstatistikk and use a direct API connection instead.
    * Recreate the associated plots from part 1 of the project using the API connection.
* Use the ENTSO-E API to retrieve cross-border transfer data from/to Norway for the last two years.
    * Insert the data into Cassandra using Spark.
* Use Spark to extract relevant columns from Cassandra.
* Create the following plots:
    * A pie chart for the total production of one year from a chosen connection, where each piece of the pie is the amount in and out of Norway.
    * A line plot for the first month of a year for a chosen connection. Make separate lines for each connection and direction.
* Insert the Spark-extracted data into your MongoDB.
* Remember to fill in the log and AI mentioned in the General section above.

#### Streamlit app

* Update your Streamlit app from part 1 of the project according to the following points.
* If you have something you would like to keep on page four, move it to a new page five.
* Establish a connection to the API of Magasinstatistikk and use this instead of the now-deleted CSV file.

* **Update 12.10**: 
    * The selection slider that was on page three should now control the download interval, i.e., which data are downloaded.
    * Use radio buttons (st.radio) to select the type of areas (EL, NO, VASS) such that plots and LineChartColumn() show the corresponding graphics (e.g., lines) for each of the associated area numbers.
    * Reorganise pages two and three in the way you find most logical and user-friendly. Use an extra page if you need to. Solutions that deviate slightly from the descriptions above, but improve the experience are welcome.
* Establish a connection with your MongoDB database. When running this at streamlit.io, remember to copy your secrets to the webpage instead of exposing them on GitHub.
* On a separate page, split the view into two columns using st.columns.
    * On the left side, use radio buttons (st.radio) to select a connection and a different control to select the year, and display a pie chart like in the Jupyter Notebook
    * On the right side, use pills (st.pills) to select which months to include and display a line plot like in the Jupyter Notebook (but for any set of months).
    * Below the columns, insert an expander (st.expander) where you briefly document the source of the data shown on the page.

#### Screencast

* 5-minute screencast where you briefly showcase your running app and explain what your code does. This description may be updated based on experiences from part 1 of the project.
* Canvas does not permit upload of more than one file in the assignment.
    * If you make a screencast in Panopto, you can share a link to your video and add the link to the Jupyter Notebook or as a submission comment (make sure the file permissions are open for anyone, as the default is locked and private).
    * If you use a different tool for making the screencast, you can upload your video to the GitHub repo.

---

#### Evaluation

* The uploaded PDF, GitHub repository, Streamlit app, and screencast will be assessed according to the recipe above.
    * By one fellow student in peer review.
    * By Liland or Osman.
* TA/Teacher's feedback will be short and instructive regarding points of improvement and fulfilment of requirements.
* Final fulfilment of the course will be based on the four rounds of hand-ins seen as a whole.
