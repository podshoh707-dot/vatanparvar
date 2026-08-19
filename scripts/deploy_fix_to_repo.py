import os
import shutil
import subprocess

src = "."
dst = os.path.join("webapp", "avtomaktab-webapp")
git_exe = r"C:\Users\user\AppData\Local\GitHubDesktop\app-3.6.4\resources\app\git\cmd\git.exe"

files_to_copy = [
    "requirements.txt",
    "runtime.txt",
    "bot.py",
    "config.py",
    "scheduler.py",
    "api_server.py",
    "Procfile",
    "render.yaml",
    "welcome.png"
]

for f in files_to_copy:
    src_f = os.path.join(src, f)
    dst_f = os.path.join(dst, f)
    if os.path.exists(src_f):
        shutil.copy2(src_f, dst_f)
        print(f"Copied {f} -> {dst_f}")

# Also ensure runtime.txt has 3.11.9
with open(os.path.join(dst, "runtime.txt"), "w") as f:
    f.write("3.11.9\n")

env = os.environ.copy()
env["PATH"] = os.path.dirname(git_exe) + ";" + env["PATH"]

subprocess.run([git_exe, "add", "-A"], cwd=dst, env=env)
res = subprocess.run([git_exe, "commit", "-m", "Fix: Add requirements.txt, runtime.txt and bot.py to root"], cwd=dst, capture_output=True, text=True, env=env)
print("Commit output:\n", res.stdout, res.stderr)
print("Done staging and committing!")
