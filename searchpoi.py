#!/usr/bin/env python
# encoding: utf-8

import os, sys, math, urllib, urllib2, time
import ctypes, socket, threading, json, Queue, sqlite3, logging
from threading import Thread

# 参考
# http://developer.baidu.com/map/index.php?title=webapi/guide/webservice-placeapi
# http://developer.baidu.com/map/index.php?title=car/api/surrounding < 分类
# http://developer.baidu.com/map/devRes.htm < 城市代码

# 其他

# http://map.baidu.com/?qt=con&wd=美食&pn=1&b=(7828889,1541100;15480217,7201773)&l=19
# http://map.baidu.com/?qt=con&wd=美食&pn=1&c=131
# http://api.map.baidu.com/?qt=s&wd=美食&c=289&rn=10&ie=utf-8&oue=1&res=api
# http://api.map.baidu.com/?qt=rgc&x=12957308.93&y=4839066.3&dis_poi=100&poi_num=10


# 定义全局变量
success = 0
mutex = threading.Lock()        # 线程锁
socket.setdefaulttimeout(15)    # 超时时间15秒
MAX_THREADS = 50                # 最大线程数
BASE_URL_C = 'http://map.baidu.com/?qt=con&wd={0}&c={1}&nn={2}'                          # 通过城市ID获取数据 注意这里用pn参数不管用只能用nn参数
BASE_URL_B = 'http://map.baidu.com/?qt=con&nn=0&wd={0}&b=({1},{2};{3},{4})&l=19&pn={5}'  # 通过范围获取数据



# POI分类
TAGS = [ u'美食', u'宾馆', u'购物', u'汽车服务', u'生活服务', u'结婚', u'丽人', u'金融', u'休闲娱乐',
         u'运动健身', u'医疗', u'旅游景点', u'教育', u'培训机构', u'交通设施', u'房地产', u'自然地物',
         u'行政区划', u'政府机构', u'公司企业', u'门址', u'道路', u'交通线' ]

# 有效城市列表
CITYS = {
        131:u'北京市',289:u'上海市',257:u'广州市',132:u'重庆市',340:u'深圳市',75:u'成都市',224:u'苏州市',315:u'南京市',
        317:u'无锡市',161:u'南通市',348:u'常州市',316:u'徐州市',223:u'盐城市',346:u'扬州市',276:u'泰州市',160:u'镇江市',
        162:u'淮安市',277:u'宿迁市',347:u'连云港市',236:u'青岛市',288:u'济南市',287:u'潍坊市',326:u'烟台市',234:u'临沂市',
        354:u'淄博市',286:u'济宁市',175:u'威海市',372:u'德州市',174:u'东营市',325:u'泰安市',353:u'菏泽市',366:u'聊城市',
        172:u'枣庄市',235:u'滨州市',173:u'日照市',124:u'莱芜市',179:u'杭州市',180:u'宁波市',178:u'温州市',333:u'金华市',
        293:u'绍兴市',244:u'台州市',334:u'嘉兴市',294:u'湖州市',243:u'衢州市',292:u'丽水市',245:u'舟山市',138:u'佛山市',
        119:u'东莞市',187:u'中山市',302:u'江门市',301:u'惠州市',140:u'珠海市',198:u'湛江市',139:u'茂名市',338:u'肇庆市',
        303:u'汕头市',259:u'揭阳市',197:u'清远市',141:u'梅州市',137:u'韶关市',199:u'阳江市',200:u'河源市',258:u'云浮市',
        201:u'潮州市',339:u'汕尾市',268:u'郑州市',153:u'洛阳市',309:u'南阳市',152:u'新乡市',214:u'信阳市',308:u'周口市',
        267:u'安阳市',155:u'许昌市',269:u'驻马店市',213:u'平顶山市',154:u'商丘市',211:u'焦作市',210:u'开封市',209:u'濮阳市',
        212:u'三门峡市',344:u'漯河市',215:u'鹤壁市',1277:u'济源市',218:u'武汉市',156:u'襄阳市',270:u'宜昌市',157:u'荆州市',
        271:u'黄冈市',216:u'十堰市',310:u'孝感市',217:u'荆门市',311:u'黄石市',373:u'恩施土家族苗族自治州',362:u'咸宁市',
        371:u'随州市',1713:u'仙桃市',1293:u'潜江市',122:u'鄂州市',2654:u'天门市',2734:u'神农架林区',300:u'福州市',
        134:u'泉州市',194:u'厦门市',255:u'漳州市',193:u'龙岩市',195:u'莆田市',133:u'南平市',192:u'宁德市',254:u'三明市',
        150:u'石家庄市',265:u'唐山市',307:u'保定市',149:u'沧州市',151:u'邯郸市',191:u'廊坊市',266:u'邢台市',264:u'张家口市',
        148:u'秦皇岛市',208:u'衡水市',207:u'承德市',167:u'大连市',58:u'沈阳市',320:u'鞍山市',282:u'丹东市',184:u'抚顺市',
        281:u'营口市',319:u'葫芦岛市',166:u'锦州市',60:u'铁岭市',351:u'辽阳市',280:u'朝阳市',228:u'盘锦市',227:u'本溪市',
        59:u'阜新市',127:u'合肥市',130:u'安庆市',129:u'芜湖市',189:u'滁州市',298:u'六安市',128:u'阜阳市',251:u'巢湖市',
        126:u'蚌埠市',250:u'淮南市',190:u'宣城市',370:u'宿州市',188:u'亳州市',252:u'黄山市',358:u'马鞍山市',253:u'淮北市',
        299:u'池州市',337:u'铜陵市',158:u'长沙市',159:u'衡阳市',222:u'株洲市',219:u'常德市',273:u'邵阳市',220:u'岳阳市',
        313:u'湘潭市',275:u'郴州市',314:u'永州市',363:u'怀化市',272:u'益阳市',221:u'娄底市',274:u'湘西土家族苗族自治州',
        312:u'张家界市',240:u'绵阳市',291:u'南充市',74:u'德阳市',369:u'达州市',79:u'乐山市',186:u'宜宾市',331:u'泸州市',
        330:u'遂宁市',242:u'资阳市',78:u'自贡市',248:u'内江市',80:u'凉山彝族自治州',329:u'广元市',241:u'广安市',239:u'巴中市',
        77:u'眉山市',81:u'攀枝花市',76:u'雅安市',185:u'阿坝藏族羌族自治州',73:u'甘孜藏族自治州',163:u'南昌市',365:u'赣州市',
        364:u'上饶市',349:u'九江市',318:u'吉安市',278:u'宜春市',226:u'抚州市',225:u'景德镇市',164:u'新余市',350:u'萍乡市',
        279:u'鹰潭市',261:u'南宁市',142:u'桂林市',305:u'柳州市',361:u'玉林市',304:u'梧州市',203:u'百色市',341:u'贵港市',
        143:u'河池市',145:u'钦州市',144:u'崇左市',295:u'北海市',202:u'来宾市',260:u'贺州市',204:u'防城港市',233:u'西安市',
        323:u'咸阳市',171:u'宝鸡市',231:u'榆林市',170:u'渭南市',352:u'汉中市',284:u'延安市',324:u'安康市',285:u'商洛市',
        232:u'铜川市',176:u'太原市',368:u'临汾市',328:u'运城市',355:u'大同市',238:u'晋中市',356:u'长治市',327:u'吕梁市',
        290:u'晋城市',367:u'忻州市',357:u'阳泉市',237:u'朔州市',104:u'昆明市',249:u'曲靖市',106:u'玉溪市',111:u'大理白族自治州',
        107:u'红河哈尼族彝族自治州',105:u'楚雄彝族自治州',336:u'昭通市',177:u'文山壮族苗族自治州',112:u'保山市',114:u'丽江市',
        108:u'普洱市',109:u'西双版纳傣族自治州',116:u'德宏傣族景颇族自治州',110:u'临沧市',113:u'怒江傈僳族自治州',
        115:u'迪庆藏族自治州',48:u'哈尔滨市',50:u'大庆市',41:u'齐齐哈尔市',49:u'牡丹江市',42:u'佳木斯市',44:u'绥化市',
        46:u'鸡西市',39:u'黑河市',45:u'双鸭山市',40:u'伊春市',43:u'鹤岗市',38:u'大兴安岭地区',47:u'七台河市',53:u'长春市',
        55:u'吉林市',54:u'延边朝鲜族自治州',56:u'四平市',165:u'通化市',52:u'松原市',57:u'白山市',183:u'辽源市',51:u'白城市',
        321:u'呼和浩特市',229:u'包头市',283:u'鄂尔多斯市',297:u'赤峰市',61:u'呼伦贝尔市',169:u'巴彦淖尔市',64:u'通辽市',
        168:u'乌兰察布市',63:u'锡林郭勒盟',123:u'乌海市',62:u'兴安盟',230:u'阿拉善盟',332:u'天津市',92:u'乌鲁木齐市',
        90:u'伊犁哈萨克自治州',86:u'巴音郭楞蒙古自治州',93:u'昌吉回族自治州',83:u'喀什地区',85:u'阿克苏地区',94:u'塔城地区',
        91:u'哈密地区',95:u'克拉玛依市',96:u'阿勒泰地区',89:u'吐鲁番地区',770:u'石河子市',88:u'博尔塔拉蒙古自治州',
        82:u'和田地区',84:u'克孜勒苏柯尔克孜自治州',731:u'阿拉尔市',789:u'五家渠市',792:u'图木舒克市',146:u'贵阳市',
        262:u'遵义市',342:u'黔东南苗族侗族自治州',306:u'黔南布依族苗族自治州',205:u'铜仁地区',263:u'安顺市',206:u'毕节地区',
        147:u'六盘水市',343:u'黔西南布依族苗族自治州',36:u'兰州市',196:u'天水市',37:u'酒泉市',135:u'庆阳市',256:u'陇南市',
        359:u'平凉市',35:u'白银市',136:u'定西市',117:u'张掖市',118:u'武威市',182:u'临夏回族自治州',34:u'金昌市',247:u'甘南藏族自治州',
        33:u'嘉峪关市',125:u'海口市',121:u'三亚市',1215:u'儋州市',2758:u'文昌市',2358:u'琼海市',2757:u'澄迈县',1216:u'万宁市',
        2634:u'东方市',1214:u'定安县',1643:u'陵水黎族自治县',1642:u'昌江黎族自治县',2032:u'乐东黎族自治县',1641:u'屯昌县',
        2359:u'白沙黎族自治县',1217:u'保亭黎族苗族自治县',2033:u'临高县',2031:u'琼中黎族苗族自治县',1644:u'五指山市',
        1218:u'西沙群岛',2912:u'香港特别行政区',360:u'银川市',335:u'石嘴山市',322:u'吴忠市',246:u'固原市',181:u'中卫市',
        66:u'西宁市',69:u'海东地区',65:u'海西蒙古族藏族自治州',68:u'海南藏族自治州',67:u'海北藏族自治州',70:u'黄南藏族自治州',
        71:u'玉树藏族自治州',72:u'果洛藏族自治州',100:u'拉萨市',102:u'日喀则地区',98:u'林芝地区',97:u'山南地区',99:u'昌都地区',
        101:u'那曲地区',103:u'阿里地区',2911:u'澳门特别行政区'
        }



##########################################################################
class Worker(Thread):
    # 线程池工作线程 只支持 python 2.7 或以上版本
    worker_count = 0
    def __init__(self, workQueue, resultQueue, timeout = 0, **kwds):
       Thread.__init__(self, **kwds)
       self.id = Worker.worker_count
       Worker.worker_count += 1
       self.setDaemon(True)
       self.workQueue = workQueue
       self.resultQueue = resultQueue
       self.timeout = timeout
       self.start()
     
    def run(self):
        ''' the get-some-work, do-some-work main loop of worker threads '''
        while True:
            try:
                callable, args, kwds = self.workQueue.get(timeout=self.timeout)
                res = callable(*args, **kwds)
                #print "worker[%2d]: %s" % (self.id, str(res))
                self.resultQueue.put(res)
            except Queue.Empty:
                break
            except :
                print 'worker[%2d]' % self.id, sys.exc_info()[:2]

class WorkerPool:
    # 线程池
    def __init__(self, num_of_workers=10, timeout = 1):
        self.workQueue = Queue.Queue()
        self.resultQueue = Queue.Queue()
        self.workers = []
        self.timeout = timeout
        self._recruitThreads(num_of_workers)
    def _recruitThreads(self, num_of_workers):
        for i in range(num_of_workers): 
            worker = Worker(self.workQueue, self.resultQueue, self.timeout)
            self.workers.append(worker)
    def wait_for_complete(self):
        # ...then, wait for each of them to terminate:
        while len(self.workers):
            worker = self.workers.pop()
            worker.join()
            if worker.isAlive() and not self.workQueue.empty():
                self.workers.append(worker)
        #print "All jobs are are completed."
    def add_job(self, callable, *args, **kwds):
        self.workQueue.put((callable, args, kwds))
    def get_result(self, *args, **kwds):
        return self.resultQueue.get(*args, **kwds)
    

##########################################################################
    

def GetHtml(url):
    # 下载网页数据 在这里可以处理链接超时 404 等错误
    # 同时这里可以设置代理或构造数据头 页面编码等
    try:
        html = urllib.urlopen(url).read().decode('utf-8')
        if (html.endswith('}}')==False): assert False, 'bad end of html!'
        else: return html
    except:
        try:
            html = urllib.urlopen(url).read().decode('utf-8')
            if (html.endswith('}}')==False): assert False, 'bad end of html!'
            else: return html
        except:
            try:
                html = urllib.urlopen(url).read().decode('utf-8')
                if (html.endswith('}}')==False): assert False, 'bad end of html!'
                else: return html
            except:
                try:
                    html = urllib.urlopen(url).read().decode('utf-8')
                    if (html.endswith('}}')==False): assert False, 'bad end of html!'
                    else: return html
                except:
                    try:
                        html = urllib.urlopen(url).read().decode('utf-8')
                        if (html.endswith('}}')==False): assert False, 'bad end of html!'
                        else: return html
                    except:
                        try:
                            html = urllib.urlopen(url).read().decode('utf-8')
                            if (html.endswith('}}')==False): assert False, 'bad end of html!'
                            else: return html
                        except:
                            return None

def GetTotal(html):
    # 解析获取总数
    try:
        decodejson = json.loads(html)
        return int(decodejson['result']['total'])
    except:
        return -1

def GetDataByCity(conn, wp, wd, city_id, node_num=0, page_size=10, total=-1):
    # 通过 城市ID遍历数据
    # conn: 数据库连接
    # wp: 线程池
    # 
    # wd: 关键字
    # city_id: 城市ID
    # node_num: 结果偏移量 对应nn参数
    # page_size: 每页记录数默认为10不能更改
    # total: 结果总数 第一页的时候total为-1
    #
    try:
        url = BASE_URL_C.format(wd, city_id, node_num)
        html = GetHtml(url)
        if (html == None):
            logging.error('error: html -> wd:{0} cid:{1}[{2}] nn:{3} ps:{4} total:{5}'.format(wd, city_id, CITYS[city_id], node_num, page_size, total))
            return
        
        if (node_num == 0):
            # 获取总数
            total = GetTotal(html)
            logging.info('wd:{0} cid:{1}[{2}] total:{3}'.format(wd, city_id, CITYS[city_id], total))

        if (node_num != 0 and city_id==131):
            logging.info('131 !! wd:{0} cid:{1}[{2}] total:{3}'.format(wd, city_id, CITYS[city_id], total))
        
        # 插入数据
        count = GetTotal(html)
        if (count < 0):
            logging.error('error: json -> wd:{0} cid:{1}[{2}] nn:{3} ps:{4} total:{5}'.format(wd, city_id, CITYS[city_id], node_num, page_size, total))
        
        mutex.acquire()
        try:
            global success
            success += 1
            cursor = conn.cursor()
            args = (wd, city_id, 0, 0, 0, 0, node_num, page_size, count, html, int(time.time()))
            cursor.execute('insert into POIDATA values(?,?,?,?,?,?,?,?,?,?,?)', args)
            if (success % 1000 == 0):
                conn.commit()
        except:
            logging.error('error: insert -> wd:{0} cid:{1}[{2}] nn:{3} ps:{4} total:{5}'.format(wd, city_id, CITYS[city_id], node_num, page_size, total))
            pass
        mutex.release()
        
        # 查找分页信息
        if (node_num == 0 and total > page_size):
            for node_num in range(page_size, total, page_size):
                # 添加任务到线程池
                wp.add_job(GetDataByCity, conn, wp, wd, city_id, node_num, page_size, total)
                if (city_id==131): logging.info('131 !! wd:{0} cid:{1}[{2}] total:{3}'.format(wd, city_id, CITYS[city_id], total))
                
            time.sleep(0.5)
            
    except:
        logging.error('error: get data -> wd:{0} cid:{1}[{2}] pn:{3} ps:{4} total:{5}'.format(wd, city_id, CITYS[city_id], node_num, page_size, total))

def GetDataByBorder(conn, wp, wd, xmin, ymin, xmax, ymax, node_num=0, page_size=10, total=-1):
    # 通过 范围遍历数据
    # wd: 关键字
    # xmin: 最小x
    # ymin: 最小y
    # xmax: 最大x
    # ymax: 最大y
    # node_num: 结果偏移量
    # page_size: 每页记录数默认为10不能更改
    # total: 结果总数 第一页的时候total为-1
    
    pass

def InitDB(conn):
    # 初始化数据库
    cu = conn.cursor()

    # 创建POIDATA表
    cu.execute(
        """create table if not exists POIDATA(
               wd varchar(20),      -- 关键字
               cityid int,          -- 城市ID
               
               xmin number,         -- 最小X
               ymin number,         -- 最小Y
               xmax number,         -- 最大X
               ymax number,         -- 最大Y
               
               rownum int,          -- 结果偏移量nn nn=0,10,20....
               pagesize int,        -- 每页结果数 默认10 不能修改
               total int,           -- 结果总数
               context text,        -- json内容
               time number)         -- 时间戳
        """)

def Init(fname):
    # 初始化日志
    logging.basicConfig(level=logging.DEBUG,
                format=r'%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt=r'%m/%d %H:%M:%S',
                filename=fname,
                filemode='a')
    # 定义一个StreamHandler，将INFO级别或更高的日志信息打印到标准错误，并将其添加到当前的日志处理对象#
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    

if __name__ == '__main__':
    #
    # 传进来参数CITY ID
    if (len(sys.argv) == 2):
        cityid = int(sys.argv[1])
    else: cityid = 0

    # 初始化
    if (os.path.exists('./output')==False):
        os.mkdir('./output')
    logfile = './output/{0}.log'.format(cityid)
    dbfile = './output/{0}.db'.format(cityid)
    Init(logfile)
    conn = sqlite3.connect(dbfile, check_same_thread = False)
    InitDB(conn)
    wp = WorkerPool(MAX_THREADS)

    # 执行任务
    if (CITYS.has_key(cityid)):
        for tag in TAGS:
            GetDataByCity(conn, wp, tag, cityid)
            time.sleep(0.1)
    else:
        logging.error('error cityid: {0}'.format(cityid))

    time.sleep(10)
    wp.wait_for_complete()              # 等待完成
    conn.commit()
    conn.close()
    
    logging.info('### {0}[{1}]: {2}'.format(cityid, CITYS.get(cityid, '未知'), success))
    



    





    
