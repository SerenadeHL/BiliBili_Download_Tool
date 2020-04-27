import requests
import re
import json
import asyncio
import urllib3
import aiohttp
import os
import shutil

urllib3.disable_warnings()
sep = os.sep
script_path = os.path.realpath(__file__)
script_dir = os.path.dirname(script_path)


class Bilibili:
    def __init__(self, bvId, sessData='', quality=64):

        self.bvId = bvId
        # sessData用于判断登录状态和是否会员，网页登录BiliBili后，按F12 Application中cookie可以找到
        self.sessData = sessData
        # quality
        # 116: 高清1080P60 (需要带入大会员的cookie中的SESSDATA才行,普通用户的SESSDATA最多只能下载1080p的视频)
        # 112: 高清1080P+ (hdflv2) (需要大会员)
        # 80: 高清1080P (flv)
        # 74: 高清720P60 (需要大会员)
        # 64: 高清720P (flv720)
        # 32: 清晰480P (flv480)
        # 16: 流畅360P (flv360)
        self.quality = quality
        self.cid = 0
        self.bvDir = script_dir + sep + 'video' + sep + self.bvId + sep
        self.piecesDir = self.bvDir + 'pieces' + sep
        self.taskFile = self.piecesDir + 'task.txt'
        self.base_url = 'https://www.bilibili.com/video/' + self.bvId
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 SE 2.X MetaSr 1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q = 0.9',
            # 登录B站后复制一下cookie中的SESSDATA字段,有效期1个月
            'Cookie': 'SESSDATA={}'.format(self.sessData),
        }

    # 请求视频下载地址时需要添加的请求头
        self.download_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 SE 2.X MetaSr 1.0',
            'Referer': 'https://www.bilibili.com/video/' + self.bvId,
            'Origin': 'https://www.bilibili.com',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, sdch, br',
            'Accept-Language': 'zh-CN,zh;q=0.8'
        }

    def getCid(self):
        # cidUrl = 'https://api.bilibili.com/x/player/pagelist?bvid=' + self.bvId
        cidUrl = 'https://api.bilibili.com/x/web-interface/view?bvid=' + self.bvId
        html = requests.get(cidUrl, headers=self.base_headers).json()
        print(json.dumps(html))
        self.info = html['data']
        self.cid = html['data']['cid']
        
    def getResponseData(self):
        playUrl = 'https://api.bilibili.com/x/player/playurl?cid={}&bvid={}&qn={}&type=&otype=json&fourk=1&fnver=0&fnval=16'.format(
            self.cid, self.bvId, self.quality)
        data = requests.get(playUrl, headers=self.base_headers).json()
        print(json.dumps(data))

        # base_response = requests.get(self.base_url,headers=self.base_headers)
        # html = base_response.text
        # window_playinfo = re.search('<script>window.__playinfo__=(.*?)</script>',html,re.S).group(1)
        # self.name = re.search('<span class="tit(.*?)">(.*?)</span>',html,re.S).group(2)
        # data = json.loads(window_playinfo)
        return data

    def mkPiecesDir(self):
        print(self.piecesDir)
        try:
            os.makedirs(self.piecesDir)
            print(1)
        except:
            pass
        else:
            pass
    
    def rmPiecesDir(self):
        try:
            print(self.piecesDir)
            shutil.rmtree(self.piecesDir)
            print(1)
        except:
            pass
        else:
            pass

    def getVideoFormat(self):
        if 'flv' in self.data['data']['format']:
            return 'flv'
        else:
            if 'mp4' in self.data['data']['format']:
                return 'mp4'

    def concatContent(self, filename):
        content = "file '"+self.piecesDir+filename+"'\n"
        return content

    def writeConcatFile(self, content):
        with open(self.taskFile, 'w') as f:
            f.write(content)
            f.close

    def videoMerge(self, taskFile, output):
        sentence = 'ffmpeg -f concat -safe 0 -i "{}" -c copy "{}.{}'.format(
            taskFile, output, self.getVideoFormat())
        print(sentence)
        os.system(sentence)
    
    def combineAV(self,videoFile,audioFile,output):
        sentence = 'ffmpeg -i "{}" -i "{}" -c copy "{}.{}'.format(
            videoFile , audioFile, output, self.getVideoFormat())
        print(sentence)
        os.system(sentence)


    async def getFileByUrl(self, url, filename):
        print(filename)
        await asyncio.sleep(1)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.download_headers, verify_ssl=False) as r:
                content = await r.read()
            with open(self.piecesDir+filename, 'wb') as f:
                f.write(content)
                f.close

    def downloadPieces(self, data):
        loop = asyncio.get_event_loop()
        coros = []
        task_content = ''
        for info in data['data']['durl']:
            filename = self.bvId + '_' + str(info['order']) + '.flv'
            task_content += self.concatContent(filename)
            coros.append(self.getFileByUrl(info['url'], filename))
        loop.run_until_complete(asyncio.gather(*coros))
        self.writeConcatFile(task_content)
        self.videoMerge(self.taskFile, self.bvDir+self.info['title'])
        pass

    def downloadAudioAndVideo(self, data):
        loop = asyncio.get_event_loop()
        coros = []
        filename = self.bvId + '.flv'
        audioFilename = self.bvId + '_audio.flv'
        coros.append(self.getFileByUrl(data['data']['dash']['audio'][0]['baseUrl'], audioFilename))
        
        for info in data['data']['dash']['video']:
            if info['id'] == self.quality:
                coros.append(self.getFileByUrl(info['baseUrl'], filename))
                break
        else: 
            coros.append(self.getFileByUrl(data['data']['dash']['video'][0]['baseUrl'], filename))
        loop.run_until_complete(asyncio.gather(*coros))
        self.combineAV(self.piecesDir+filename,self.piecesDir+audioFilename,self.bvDir+self.info['title'])
        pass


    def run(self):
        self.getCid()
        self.data = self.getResponseData()
        self.mkPiecesDir()
        if('dash' in self.data['data'].keys()):
            self.downloadAudioAndVideo(self.data)
        else:
            self.downloadPieces(self.data)
        self.rmPiecesDir()

bvId = 'BV1qs411b7uC'
sessData = '5ba8ed9c%2C1603209842%2C1adf2*41'
quality = 64
tool = Bilibili(bvId, sessData, quality)
tool.run()