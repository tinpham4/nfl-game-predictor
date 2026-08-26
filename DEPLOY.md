# Deploying this app

Streamlit Community Cloud hosts this for free and gives you a public URL like
`https://nfl-game-predictor.streamlit.app`. That's the link you put on your
resume.

Total time: about 10 minutes, most of it waiting for the build.

---

## Before you start

You need a GitHub account. If you don't have one, make it at
[github.com/signup](https://github.com/signup) first - use a username you're
happy for recruiters to see, since it becomes part of the URL of every project
you post.

---

## Step 1 - Get the code onto your Mac

Unzip the project folder somewhere you'll find it again, like
`~/Documents/nfl-game-predictor`.

Open Terminal (Cmd+Space, type "Terminal") and go to that folder:

```bash
cd ~/Documents/nfl-game-predictor
```

Check you're in the right place - this should list `app.py`, `build_data.py`
and a `data` folder:

```bash
ls
```

## Step 2 - Check it runs locally first

Never deploy something you haven't seen work. Install and run it:

```bash
pip3 install -r requirements.txt
streamlit run app.py
```

Your browser should open to the app. Click around both tabs, switch teams.

When you're done, press `Ctrl+C` in Terminal to stop it.

**If `pip3` isn't found:** you need Python. Install it from
[python.org/downloads](https://www.python.org/downloads/), then try again.

**If you get a "externally-managed-environment" error,** use a virtual
environment instead - this is the clean way anyway:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Step 3 - Push it to GitHub

Make a new empty repository at
[github.com/new](https://github.com/new). Name it `nfl-game-predictor`. Set it
to **Public** (Streamlit's free tier needs public repos). Do **not** tick
"Add a README" - you already have one.

GitHub will show you a page with commands. Ignore those and use these instead,
replacing `YOUR-USERNAME`:

```bash
git init
git add .
git commit -m "NFL game predictor - Streamlit app"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/nfl-game-predictor.git
git push -u origin main
```

Refresh the GitHub page. Your files should be there, including the `data`
folder.

**Confirm `data/` actually uploaded.** This is the one thing that quietly breaks
the deploy. The `.gitignore` is already set up to include it, but check the
folder is visible on GitHub before moving on. If it's missing, the deployed app
will start and then tell you it can't find its data files.

## Step 4 - Deploy

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   GitHub. Authorize it when asked.
2. Click **Create app**, then **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `YOUR-USERNAME/nfl-game-predictor`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** pick something clean, like `nfl-game-predictor`
4. Click **Deploy**.

You'll watch a build log for two or three minutes while it installs the
packages. When it finishes, your app is live at that URL.

---

## Keeping it current

The predictions are frozen at whatever `build_data.py` last produced. To refresh
them during the season:

```bash
pip install -r requirements-dev.txt   # only needed the first time
python build_data.py
git add data/
git commit -m "Refresh predictions"
git push
```

Streamlit Cloud redeploys automatically within a minute of the push. Nothing
else to do.

Doing this a few times through the season is worth it beyond just accuracy - a
repo with commits spread across months reads as a project you maintained, not a
weekend you spent.

---

## If something goes wrong

**"Error installing requirements"** - open the build log and find the first red
line. Usually it's a version that doesn't exist for the Python version Streamlit
picked. In the app's settings, set Python to **3.11** and reboot it.

**App loads but says it can't find the data files** - `data/` didn't get pushed.
Check it's visible in your GitHub repo. If not:

```bash
git add -f data/
git commit -m "Add data files"
git push
```

**App is stuck "in the oven" or spinning** - free apps sleep after a week
without visitors. Opening the URL wakes it back up; the first load takes about
30 seconds. Worth knowing before you send the link to a recruiter - click it
yourself first.

**Anything else** - the build log is at the bottom right of the app page
("Manage app"). The first error in it is almost always the real one.

---

## For your resume

Once it's live, the line writes itself if you keep it concrete:

> **NFL Game Predictor** - Python, scikit-learn, pandas, Streamlit
> Logistic regression predicting NFL game winners from rolling EPA efficiency
> data across 10 seasons (345k plays). 63.2% accuracy on 543 held-out games vs.
> a 53.6% baseline, with calibrated confidence (70%+ picks hit 78%). Live at
> [your-url].

Lead with the held-out number and the baseline next to it. Plenty of student
projects report an accuracy figure; far fewer show they know what to compare it
against, or that they checked whether the model's confidence means anything.
That comparison is the part worth talking about in an interview.
