To serve a local file for pyscript
https://developer.mozilla.org/en-US/docs/Learn/Common_questions/set_up_a_local_testing_server

cd/D my_directory
rem will serve on 8000
python -m http.server

http://localhost:8000/

rem or else to serve on 8765
python -m http.server 8765

http://localhost:8765/

There is a DRAFt File System API supported in Chrome but not in Firefox or Safari. (June 2022)
https://wicg.github.io/file-system-access/

url = 'https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2020/2020-07-28/penguins.csv'
      penguins = pd.read_csv(open_url(url)).dropna()