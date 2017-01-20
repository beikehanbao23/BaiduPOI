#!/usr/bin/env python
# encoding: utf-8

import os, sys, math, sqlite3

# 百度墨卡托坐标
# 参考:
# http://blog.163.com/ruby_study/blog/static/238680065201489103958382/
# https://gist.github.com/aisk/3735854
# http://www.4wei.cn/archives/1002008
# https://gist.github.com/chao-he/7747495

# 百度坐标转换
# GPS坐标 -> 火星坐标 -> 百度坐标
# 关键字 GCJ-02 BD-09 wgtochina_lb 二分法
# GPS坐标 -> 火星坐标 (单向不可逆 算法wgtochina_lb 逆向求解可用二分法)
# http://blog.csdn.net/xiaobaismiley/article/details/37576303
# https://on4wp7.codeplex.com/SourceControl/changeset/view/21483#353936
# http://blog.csdn.net/giswens/article/list/4
# http://www.gpsspg.com/maps.htm
# https://github.com/scateu/PyWGS84ToGCJ02 < 这里有计算距离的
# https://code.google.com/p/my-android-util/source/browse/trunk/src/com/android/util/location/Converter.java?spec=svn2&r=2 < wgtochina_lb 算法
# http://www.oschina.net/code/snippet_260395_39205


class BaiduMercator:
    # 百度墨卡托坐标
    EARTHRADIUS = 6370996.81
    MCBAND = [12890594.86, 8362377.87, 5591021, 3481989.83, 1678043.12, 0]
    LLBAND = [75, 60, 45, 30, 15, 0]
    MC2LL = [
        [1.410526172116255e-8, 0.00000898305509648872, -1.9939833816331, 200.9824383106796, -187.2403703815547, 91.6087516669843, -23.38765649603339, 2.57121317296198, -0.03801003308653, 17337981.2],
        [ - 7.435856389565537e-9, 0.000008983055097726239, -0.78625201886289, 96.32687599759846, -1.85204757529826, -59.36935905485877, 47.40033549296737, -16.50741931063887, 2.28786674699375, 10260144.86], 
        [ - 3.030883460898826e-8, 0.00000898305509983578, 0.30071316287616, 59.74293618442277, 7.357984074871, -25.38371002664745, 13.45380521110908, -3.29883767235584, 0.32710905363475, 6856817.37],
        [ - 1.981981304930552e-8, 0.000008983055099779535, 0.03278182852591, 40.31678527705744, 0.65659298677277, -4.44255534477492, 0.85341911805263, 0.12923347998204, -0.04625736007561, 4482777.06],
        [3.09191371068437e-9, 0.000008983055096812155, 0.00006995724062, 23.10934304144901, -0.00023663490511, -0.6321817810242, -0.00663494467273, 0.03430082397953, -0.00466043876332, 2555164.4],
        [2.890871144776878e-9, 0.000008983055095805407, -3.068298e-8, 7.47137025468032, -0.00000353937994, -0.02145144861037, -0.00001234426596, 0.00010322952773, -0.00000323890364, 826088.5]
    ]
    LL2MC = [
        [ - 0.0015702102444, 111320.7020616939, 1704480524535203, -10338987376042340, 26112667856603880, -35149669176653700, 26595700718403920, -10725012454188240, 1800819912950474, 82.5],
        [0.0008277824516172526, 111320.7020463578, 647795574.6671607, -4082003173.641316, 10774905663.51142, -15171875531.51559, 12053065338.62167, -5124939663.577472, 913311935.9512032, 67.5],
        [0.00337398766765, 111320.7020202162, 4481351.045890365, -23393751.19931662, 79682215.47186455, -115964993.2797253, 97236711.15602145, -43661946.33752821, 8477230.501135234, 52.5],
        [0.00220636496208, 111320.7020209128, 51751.86112841131, 3796837.749470245, 992013.7397791013, -1221952.21711287, 1340652.697009075, -620943.6990984312, 144416.9293806241, 37.5],
        [ - 0.0003441963504368392, 111320.7020576856, 278.2353980772752, 2485758.690035394, 6070.750963243378, 54821.18345352118, 9540.606633304236, -2710.55326746645, 1405.483844121726, 22.5],
        [ - 0.0003218135878613132, 111320.7020701615, 0.00369383431289, 823725.6402795718, 0.46104986909093, 2351.343141331292, 1.58060784298199, 8.77738589078284, 0.37238884252424, 7.45]
    ]


    def PixelToPoint(sefl, point, zoom, center, bounds):
        # 像素到坐标
        zoomUnits = self.GetZoomUnits(zoom)
        mercatorx = center.lng + zoomUnits * (point.x - bounds.width / 2)
        mercatory = center.lat - zoomUnits * (point.y - bounds.height / 2)
        return self.MercatorToLngLat(mercatorx, mercatory)

    def PointToPixel(self, coord, zoom, center, bounds):
        # 坐标到像素
        point = self.LngLatToMercator(coord)
        units = self.GetZoomUnits(zoom)
        x = round((point.lng - center.lng) / units + bounds.width / 2)
        y = round((center.lat - point.lat) / units + bounds.height / 2)
        return BDPoint(x, y)

    def GetZoomUnits(self, zoom):
        # 获取分辨率
        return pow(2, (18-zoom))



##################################################################################################
    def MercatorToPixel(self, x, y, zoom):
        # 墨卡托坐标转像素坐标
        pixelX = math.floor(x * math.pow(2, zoom - 18))
        pixelY = math.floor(y * math.pow(2, zoom - 18))
        return pixelX, pixelY

    def PixelToTile(self, pixelX, pixelY):
        # 像素坐标转瓦片XY 图块坐标
        tileX = int(math.floor(pixelX / 256))
        tileY = int(math.floor(pixelY / 256))
        return tileX, tileY
    
    def MercatorToLngLat(self, x, y):
        # 墨卡托坐标转经纬度
        # x: X坐标 (经度)
        # y: Y坐标 (纬度)
        # return: lng, lat 经度, 纬度
        mc = None
        absx = abs(x)
        absy = abs(y)
        for i in range(0, len(self.MCBAND)):
            if (absy >= self.MCBAND[i]):
                mc = self.MC2LL[i]
                break
        lng, lat = self.Convertor(x, y, mc)
        lng = round(lng, 6)
        lat = round(lat, 6)
        return lng, lat

    def LngLatToMercator(self, lng, lat):
        # 经纬度转墨卡托坐标
        # lng: 经度
        # lat: 纬度
        # return: X, Y 墨卡托平面坐标XY
        mc = None
        lng = self.GetLoop(lng, -180, 180)
        lat = self.GetRange(lat, -74, 74)

        for i in range(0, len(self.LLBAND)):
            if lat > self.LLBAND[i]:
                mc = self.LL2MC[i]
                break
        if mc == None:
            for i in range(len(self.LLBAND)-1, -1, -1):
                if (lat <= -self.LLBAND[i]):
                    mc =  self.LL2MC[i]
                    break
        x, y = self.Convertor(lng, lat, mc)
        x = round(x, 2)
        y = round(y, 2)
        return x, y

    def GetLoop(self, lng, a, b):
        # 经度范围
        while (lng > b):
            lng -= b - a
        while (lng < a):
            lng += b - a
        return lng

    def GetRange(self, lat, a, b):
        # 纬度范围
        lat = max(lat, a)
        lat = min(lat, b)
        return lat

    def Convertor(self, xlng, ylat, mc):
        # 数据转换
        # xlng:     X 或者 经度
        # ylat:     Y 或者 纬度
        # mc:       转换对照表
        # return:   经纬度 或 XY
        newxlng = mc[0] + mc[1] * abs(xlng)
        c = abs(ylat) / mc[9]
        newylat = mc[2] + mc[3] * c + mc[4] * c * c + mc[5] * c * c * c + mc[6] * c * c * c * c + mc[7] * c * c * c * c * c + mc[8] * c * c * c * c * c * c
        if(xlng < 0): newxlng *= -1
        if(ylat < 0): newylat *= -1
        return newxlng, newylat
##################################################################################################




PI              = 3.14159265358979324
EARTH_RADIUS    = 6378245.0
EE              = 0.00669342162296594323
X_PI            = 3.14159265358979324 * 3000.0 / 180.0

class BaiduConvert:
    # 百度坐标转换
    def OutOfChina(self, lat, lng):
        # 坐标是否在中国外
        if (lng < 72.004 or lng > 137.8347):
            return True
        if (lat < 0.8293 or lat > 55.8271):
            return True
        return False

    def TransformLat(self, x, y):
        # 纬度转换
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * PI) + 40.0 * math.sin(y / 3.0 * PI)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * PI) + 320 * math.sin(y * PI / 30.0)) * 2.0 / 3.0
        return ret

    def TransformLng(self, x, y):
        # 经度转换
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * PI) + 40.0 * math.sin(x / 3.0 * PI)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * PI) + 300.0 * math.sin(x / 30.0 * PI)) * 2.0 / 3.0
        return ret

    def GPS2Mars(self, wglat, wglng):
        # 地球坐标转换为火星坐标
        # wglat WGS纬度
        # wglng WGS经度
        # 返回近似火星坐标系
        if (self.OutOfChina(wglat, wglng)):
            return wglat, wglng
        dlat = self.TransformLat(wglng - 105.0, wglat - 35.0)
        dlng = self.TransformLng(wglng - 105.0, wglat - 35.0)
        radlat = wglat / 180.0 * PI
        magic = math.sin(radlat)
        magic = 1 - EE * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((EARTH_RADIUS * (1 - EE)) / (magic * sqrtmagic) * PI)
        dlng = (dlng * 180.0) / (EARTH_RADIUS / sqrtmagic * math.cos(radlat) * PI)
        mglat = wglat + dlat
        mglng = wglng + dlng
        return mglat, mglng

    def Mars2GPS(self, gclat, gclng):
        # 采用二分法 火星坐标反算地球坐标
        # gclat 火星坐标纬度
        # gclng 火星坐标经度
        initDelta = 0.01
        threshold = 0.000000001
        dlat = initDelta
        dlng = initDelta
        mlat = gclat - dlat
        mlng = gclng - dlng
        plat = gclat + dlat
        plng = gclng + dlng
        wgslat = 0
        wgslng = 0
        i = 0
        while (True):
            wgslat = (mlat + plat) / 2.0
            wgslng = (mlng + plng) / 2.0
            tmplat, tmplng = self.GPS2Mars(wgslat, wgslng)
            dlat = tmplat - gclat
            dlng = tmplng - gclng

            if ((abs(dlat)<threshold) and (abs(dlng)<threshold)):
                break
            if (dlat > 0): plat = wgslat
            else: mlat = wgslat
            if (dlng > 0): plng = wgslng
            else: mlng = wgslng

            i += 1
            if (i>10000): break
        return wgslat, wgslng
        
        pass
        
    def BD_encrypt(self, gglat, gglng):
        # 火星坐标转换为百度坐标
        # gglat 火星纬度
        # gglng 火星经度
        x = gglng
        y = gglat
        z = math.sqrt(x*x + y*y) + 0.00002 * math.sin(y * X_PI)
        theta = math.atan2(y, x) + 0.000003 * math.cos(x * X_PI)
        bdlng = z * math.cos(theta) + 0.0065
        bdlat = z * math.sin(theta) + 0.006
        return bdlat, bdlng

    def BD_decrypt(self, bdlat, bdlng):
        # 百度坐标转火星坐标
        x = bdlng - 0.0065
        y = bdlat - 0.006
        z = math.sqrt(x*x + y*y) - 0.00002 * math.sin(y * X_PI)
        theta = math.atan2(y, x) - 0.000003 * math.cos(x * X_PI)
        gglng = z * math.cos(theta)
        gglat = z * math.sin(theta)
        return gglat, gglng

    def BDAPI(self, lat, lng):
        # 百度官方API接口
        # http://api.map.baidu.com/ag/coord/convert?from=2&to=4&mode=1&x=116.3786889372559,116.38632786853032&y=39.90762965106183,39.90795884517671
        ifrom = 1
        ito = 5
        ak = 'M034idvG2MFv63UnDBvCHWq9'
        coords = '{0},{1}'.format(lng, lat)
        url = 'http://api.map.baidu.com/geoconv/v1/?from={0}&to={1}&ak={2}&coords={3}'.format(ifrom, ito, ak, coords)
        html = urllib.urlopen(url).read().decode('utf-8')
        decodejson = json.loads(html)
        bdlng = decodejson['result'][0]['x']
        bdlat = decodejson['result'][0]['y']
        return bdlat, bdlng


def GetData(connuid, uid):
    # 根据UID获取坐标信息
    cu = connuid.cursor()
    sql = 'select x, y, zoom, mx, my, time from UIDS where uid=\'{0}\''.format(uid)
    cu.execute(sql)
    row = cu.fetchone()
    if (row==None):
        print uid
        return None
    else:
        return {
                'uid': uid,
                'x': row[0],
                'y': row[1],
                'zoom': row[2],
                'mx': row[3],
                'my': row[4],
                'time': row[5],
               }

def GetCoorData(connuid, uid):
    # 获取坐标信息
    data = GetData(connuid, uid)
    if (data == None): return None
    # 百度墨卡托 => 百度经纬度
    baiduMC = BaiduMercator()
    bdlng, bdlat = baiduMC.MercatorToLngLat(data['mx'], data['my'])

    # 百度经纬度 => 火星坐标 => GPS坐标
    baiduConvert = BaiduConvert()
    hhlat, hhlng = baiduConvert.BD_decrypt(bdlat, bdlng)
    lat, lng = baiduConvert.Mars2GPS(hhlat, hhlng)
    # 
    data['lat'] = lat
    data['lng'] = lng
    data['bdlat'] = bdlat
    data['bdlng'] = bdlng
    data['uid'] = uid
    return data


if __name__ == '__main__':
    #
    connuid = sqlite3.connect('./data/alluid.db')
    connpoi = sqlite3.connect('./data/allpoi.db')
    
    #
    cu = connpoi.cursor()

    # 清空数据
    #cu.execute('update POIS set x=1')
    #connpoi.commit()

    cu.execute('select uid from POIS where x=1')
    table = cu.fetchall()

    num = 0
    total = len(table)
    
    for row  in table:
        num += 1
        uid = row[0].strip()
        data = GetCoorData(connuid, uid)
        if (data == None): continue
        # 插入数据
        args = (
                data['x'],
                data['y'],
                data['zoom'],
                data['lat'],
                data['lng'],
                data['bdlat'],
                data['bdlng'],
                data['time'],
                data['uid']
               )
        cu.execute('update POIS set x=?, y=?, zoom=?, lat=?, lng=?, bdlat=?, bdlng=?, time=? where uid=?', args)
        #
        if (num % 5000 == 0):
            connpoi.commit()
            print '{0}/{1}'.format(num, total)

    
    connpoi.commit()
    connuid.close()
    connpoi.close()
    print 'OK'
    
