from urllib.parse import quote
from urllib import request
import requests, random, json, os, subprocess, time
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from bs4 import BeautifulSoup

username, password = open("credentials.cfg", "r").read().split("\n") if os.path.isfile("credentials.cfg") else (input("Username: "), input("Password: "))
if not os.path.isfile("credentials.cfg"):
    if input("Remember me? (y/n): ").lower() == "y":
        open("credentials.cfg", "w").write(f"{username}\n{password}")

session = requests.Session()
session.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4093.3 Safari/537.36"}

def localizeToUs():
    print("Fetching session id...")
    res = session.get("https://api1.cr-unblocker.com/getsession.php?version=1.1")
    if res:
        sessionData = res.json()["data"]
        if sessionData["country_code"] == "US":
            print(f"Got session id, setting cookie {sessionData['session_id']}.")
            session.cookies.set(**{"name": "session_id",
                                   "value": sessionData["session_id"],
                                   "domain": f"crunchyroll.com/videos/anime/alpha?group=all",})
            session.cookies.set(**{"name": "c_locale",
                                   "value": "enUS",
                                   "domain": f"crunchyroll.com/videos/anime/alpha?group=all",})
            if not "header_profile_dropdown" in session.get("https://crunchyroll.com").text:
                data = session.post(f"https://api.crunchyroll.com/login.0.json?session_id={sessionData['session_id']}&locale=enUS&account={quote(username)}&password={quote(password)}").json()["data"]
                if data != None:
                    print(f"User logged in until {data['expires']}")
                else:
                    return False
            return True

if localizeToUs():
    animeString = session.get("https://crunchyroll.com/videos/anime/alpha?group=all").text
    soup = BeautifulSoup(animeString, "html.parser")
    animeList = [(a["title"], a["href"]) for a in soup.find_all("a", {"class": "text-link ellipsis"})]
    while True:
        sameLangForAll = None
        sameResForAll = None
        for a in range(len(animeList)):
            print(f"{a}: {animeList[a][0]}")
        seasonString = session.get(f"https://crunchyroll.com{animeList[int(input('Anime > '))][1]}").text
        soup = BeautifulSoup(seasonString, "html.parser")
        seasonList = []
        episodeList = []
        if soup.find("ul", {"class": "list-of-seasons cf"}).find("li")["class"] == ["season"]:
            episodeList = [(e.find("img")["alt"], e["href"]) for e in soup.find("li", {"class": "season"}).find_all("a")]
        else:
            seasonList = [(s.find("a")["title"], [(e.find("img")["alt"], e["href"]) for e in s.find_all("a")[1:]]) for s in soup.find_all("li", {"class": "season small-margin-bottom"})]
        if len(seasonList) > 0:
            for s in range(len(seasonList)):
                print(f"{s}: {seasonList[s][0]}")
            episodeList = seasonList[int(input("Season > "))][1]
        #episodeList = [(e[0], json.loads(session.get(f"https://crunchyroll.com{e[1]}").text.split("vilos.config.media = ")[1].split(";\n")[0])) for e in episodeList]#NEW (temporary)
        episodesToDownload = []
        while True:
            print("-1: Start Download")
            for e in range(len(episodeList)):
                print(f"{e}: {episodeList[len(episodeList)-e-1][0]}")
            i = int(input("Episode > "))
            if i == -1:
                break
            elif not episodeList[len(episodeList)-i-1] in episodesToDownload:
                episodesToDownload.append(episodeList[len(episodeList)-i-1])
        file_dest = input("Download destination: ")
        for e in episodesToDownload:
            videodata = json.loads(session.get(f"https://crunchyroll.com{e[1]}").text.split("vilos.config.media = ")[1].split(";\n")[0])
            #videodata = e[1]#NEW (temporary)
            streams = videodata["streams"]
            currTitle = f"Episode {videodata['metadata']['display_episode_number']} - {videodata['metadata']['title']}"
            print(f"--------{currTitle}--------")
            subtitleList = []
            for s in [s0 for s0 in streams if s0["format"] in ["adaptive_hls", "trailer_hls"]]:
                subtitleList.append((f"{s['hardsub_lang']} ({s['format'][:-4]})".replace(" (adaptive)", ""), s["url"]))
            i = 0
            if type(sameLangForAll) == str:
                i = [sl[0] for sl in subtitleList].index(sameLangForAll)
            else:
                for sl in range(len(subtitleList)):
                    print(f"{sl}: {subtitleList[sl][0]}")
                i = int(input("Subtitle Language > "))
                if sameLangForAll == None:
                    sameLangForAll = [False, subtitleList[i][0]][input("Use same subtitle language for all? (y/n): ").lower() == "y"]
            currURL = subtitleList[i][1]
            test3 = [str(l)[2:][:-1] for l in request.urlopen(currURL).readlines()]
            availResolutions = [(test3[l].split(",RESOLUTION=")[1].split(",")[0], test3[l+1]) for l in range(len(test3)) if "#EXT-X-STREAM-INF" in test3[l]]
            selected = ""
            if len(availResolutions) > 0:
                i = 0
                if type(sameResForAll) == str:
                    i = [r[0] for r in availResolutions].index(sameResForAll)
                else:
                    for r in range(len(availResolutions)):
                        print(f"{r}: {availResolutions[r][0]}")
                    i = int(input("Resolution > "))
                    if sameResForAll == None:
                        sameResForAll = [False, availResolutions[i][0]][input("Use same resolution for all? (y/n): ").lower() == "y"]
                selected = availResolutions[i][1]
                time.sleep(5)#TEST
            print("Downloading chunk list...")
            tmpcl = [str(l) for l in request.urlopen(selected).readlines()] if len(availResolutions) > 0 else [f"  {l}\\n " for l in test3]
            keyurl = [l.split("URI=\"")[1].split("\"\\n")[0] for l in tmpcl if "#EXT-X-KEY:METHOD=AES-128" in l][0]
            key = request.urlopen(keyurl).read()
            print(key)
            chunklist = [tmpcl[l+1].replace("\\n", "") for l in range(len(tmpcl)) if "#EXTINF" in tmpcl[l]]
            print("Done, downloading chunks...")
            if not os.path.isdir("temp"):
                os.mkdir("temp")
            for c in range(len(chunklist)):
                request.urlretrieve(chunklist[c][2:][:-1], f"temp/{c}.ts")
                print(f"{c+1} of {len(chunklist)} done...")
                time.sleep(1)#TEST
            print("Done, decoding and combining chunks...")
            filepath = os.path.join(file_dest, f"{currTitle}.ts")
            with open(filepath, "wb") as f0:
                tmpdirlen = len(os.listdir("temp"))
                for f1 in range(tmpdirlen):
                    f2 = open(os.path.join("temp", f"{f1}.ts"), "rb")
                    f0.write(unpad(AES.new(key, AES.MODE_CBC, iv=f2.read(16)).decrypt(f2.read()), AES.block_size))
                    f2.close()
                    os.remove(os.path.join("temp", f"{f1}.ts"))
                    print(f"{f1+1} of {tmpdirlen} done...")
                f0.close()
            os.rmdir("temp")
            print("Done, converting file to mp4...")
            done = subprocess.Popen(f"ffmpeg.exe -i \"{filepath}\" -c:v libx264 -c:a aac \"{filepath[:-2]}mp4\"", stdout=subprocess.PIPE, shell=True).wait()
            os.remove(filepath)
            print("Done!")
print("Initialization failed!")
