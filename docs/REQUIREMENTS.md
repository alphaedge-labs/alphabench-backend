Design backend application and database with fastapi and postgresql. It should not use ORM at all. I want raw sql queries. The application is such:

1. User can come to the application (frontend) and login/signup via google
2. They face a form they can submit which is a backtesting form which contains fields 'instrument_symbol', 'from_date', 'to_date', 'strategy_description'. This request is taken and stored in database. strategy_description is passed to openai or any other llm to generate a short title for described strategy. uuid and short title sent back to user as response.
3. This request is queued in backend where it goes through the following pipeline
    1. Using an llm, from the described strategy a very detailed python file is generated, with detailed logs in script such that an insightful backtesting report can be generated from this log, which will be used to backtest that strategy. List of data points that are required for this backtest to run are also given out.
    2. For the requested instrument symbol, from date, to date, the requested data points are fetched from historical data table
    3. Two files are generated from this fetched data. One being a small csv that will be used to validate successful running of obtained backtesting script. One being the actual full csv data file from which backtesting report will be generated.
    4. Python file, small dataset csv, full dataset csv are stored together in an s3 folder with request id being folder name
    5. This request is again queued for another worker which is responsible for the following pipeline
        1. Fetches backtesting script from s3 bucket and passes small dataset csv as `—data` argument to the script
        2. If the script successfully runs then small dataset csv is deleted from the s3 folder
        3. If the script runs unsuccessfully then error as python file are passed to llm again in order to fix the script. Step 5 repeats again after that.
    6. After running the above pipeline another worker is responsible for the following:
        1. Fetches backtesting script which can run successfully and passes full dataset csv as `—data` argument to the script
        2. Saves log file generated to the same s3 bucket as the file
        3. Marks in database that against that request id, `ready_for_report` field is a boolean field which tells if log file is ready to generate backtesting report
    7. After running full backtest, another worker is responsible for the following:
        1. For all requested reports if they have `ready_for_report` field marked as true then log file is fetched from that s3 folder and contents of log file are passed to another llm to analyze the contents of this log file and generate a backtesting report in markdown format
        2. This markdown formatted report is saved in same s3 folder and `generated_report` field is marked as true in database against that request with markdown report file url saved in database.
4. If the user has not logged in or signed up via google then based on its ip address and MAC address and other available details, user is still created in database but they are restricted to generation of maximum 3 reports per day
5. If the user has logged in and authenticated with google then they are limited to total of 5 reports per day.
6. If the user has logged in and authenticated with google, and they have paid for a monthly subscription plan then they can generate ’n’ total reports per day where ’n’ is specified in subscription plan and configurable from database for that particular user.
7. There are other apis in the application which are application related like:
    1. Fetch all subscription plans
    2. Fetch user’s active subscription state
    3. Fetch user profile
    4. Fetch list of reports requested by user
    5. Fetch a particular report requested by the user
