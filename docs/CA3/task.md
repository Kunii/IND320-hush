# Project work, part 3 - Data quality

Subject to minor adjustments/clarifications before the deadline.

**28.10**: Streamlit description adjusted; missing screencast description added.

## General

* **If you push new updates to the main branch of your GitHub repository before the peer review and teacher feedback, things will get cluttered.**
    * Create and use a new branch in the GitHub repository for new updates.
    * When peer review 2 and feedback 2 are finished, merge your changes into the main branch (see figure in Padlet).

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
        * This is an online version of the project, accessing data that has been uploaded to your MongoDB database and data directly downloaded from Magasinstatistikk's API and open-meteo.com's API.
        * The code, hosted on GitHub, must include relevant comments from the Jupyter Notebook and further comments regarding Streamlit usage.

* There are four parts in the project work, building on each other and resulting in a final portfolio and app to be presented at the end of the semester.
* Co-operation is applauded, and the use of AI tools is encouraged.

---

### Tasks

#### Accounts and repositories

* Reuse your account, repository and Streamlit app from the previous part of the project work.
* **Until peer review 2 and feedback 2 have been completed, [push to a temporary GitHub branch](https://nmbu.instructure.com/courses/14185/pages/git-guide-merging-diverged-branches) for later merging.**

#### API

* Familiarise yourself with the API connection at https://open-meteo.com/en/docs.
    * Observe how you can select features and produce Python code.
    * Be aware of multiple sub-sections that alter which type of data is selected.

#### Jupyter Notebook

* Navigate to https://atlas.nve.no to locate and download the shapefiles corresponding to the electricity areas and precipitation areas that correspond to the Magasinstatistikk data. Note: East is split into RS+RØ, and North is split into RM+RN.
    * Randomly sample 1000 locations in each region to use for weather data download.
* Use the open-meteo API to retrieve hourly historical **reanalysis data using the ERA5 model** for a single location as follows:
    * Create a function for the API download task that takes a region identifier plus a time interval as input, looks up the corresponding list of pairs of longitude and latitude values and downloads at least precipitation and temperature, but include any relevant property you find.
    * Apply the function to download data for NO3 for 2024.
* Outliers and anomalies:
    * Plot the average precipitation as a function of time.
    * Perform a high-pass filtering of the precipitation using the Discrete Cosine Transform to create seasonally adjusted temperature variations (SATV).
    * Add curves to the plot indicating Statistical Process Control boundaries between inliers and outliers based on the SATV according to robust statistics estimated from the whole year. Colour outliers with a contrasting colour. Do not plot SATV values; only use them to find boundaries and outliers.
    * Let the frequency cut-off for the DCT and the number of standard deviations be parameters with sensible defaults.
    * Wrap this in a function that returns the plot and relevant summaries of the outliers, and test the function.
* Plot the average temperature as a function of time.
    * Indicate anomalies according to the Local Outlier Factor method.
    * Let the proportion of outliers be a parameter defaulting to 1%.
    * Wrap this in a function that returns the plot and relevant summaries of the outliers, and test the function.
* Seasonal-Trend decomposition using LOESS (STL)
    * Perform STL on the degree of filling from the magasinstatistikk data and plot its decomposition.
    * Let the seasonal smoother, trend smoother and robust (true/false) be parameters, and give each of them sensible defaults.
    * Wrap this in a function that returns the plot, and test the function.
* Spectrogram
    * Create a spectrogram based on the same data.
    * Let the window length and window overlap be parameters, and give each of them sensible defaults.
    * Wrap this in a function that returns the plot, and test the function.
* Remember to fill in the log and AI mentioned in the General section above.

#### Streamlit app

* Update your Streamlit app from part 2 of the project according to the following points.
    * Note! For each of the new pages below, consider whether you can depend on an existing area selector or need a local one. Also, consider if this should be a global or local setting.
* Meteorological data:
    * Let the choice of downloaded data depend on the selector that is used for the magasinstatistikk.
    * Consider if you need a separate page for download control and confirmation, or if this can be an integrated, hidden part of the web app.
* On one new page, use st.tabs() and fill the first tab with the STL analysis and the second tab with the Spectrogram. Add necessary UI elements and plots to both.
* On a second new page, use st.tabs() and fill the first tab with the Outlier/SPC analysis and the second tab with the Anomaly/LOF analysis. Add necessary UI elements, plots and statistics to both.
* Reorder any pages according to good logic and natural grouping.

#### Screencast

* 5-minute screencast where you briefly showcase your running app and explain what your code does.
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
