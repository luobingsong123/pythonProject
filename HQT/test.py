import subprocess

def get_installed_packages():
    result = subprocess.run(["pip", "freeze"], capture_output=True, text=True)
    return result.stdout

logs=open("requirements.txt","w")
logs.write(get_installed_packages())