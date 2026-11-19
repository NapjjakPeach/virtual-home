import cv2, numpy as np, json, sys
cap=cv2.VideoCapture(sys.argv[1]); out=sys.argv[2]
def frame(t):
    cap.set(1,int(round(t*24))); ok,f=cap.read(); return f.astype(np.float32)
def seamless(img):
    h,w=img.shape[:2]
    r=np.roll(np.roll(img,h//2,0),w//2,1)
    yy=np.abs(np.linspace(-1,1,h))[:,None]; xx=np.abs(np.linspace(-1,1,w))[None,:]
    m=np.clip((1-np.maximum(yy,xx))*2.2,0,1)[...,None]
    return img*m+r*(1-m)
def flatten(img,sigma,target=None):
    blur=cv2.GaussianBlur(img,(0,0),sigma)
    mean=img.reshape(-1,3).mean(0) if target is None else np.array(target,np.float32)
    return np.clip(img/np.maximum(blur,1)*mean,0,255)
def warp(f,A,B,D,W,H):
    src=np.float32([A,B,D]); dst=np.float32([[0,0],[W,0],[0,H]])
    M=cv2.getAffineTransform(src,dst); return cv2.warpAffine(f,M,(W,H),flags=cv2.INTER_CUBIC)
res={}
# 1) 마루: 4.75s 거실 바닥 그늘 부분, 판 방향에 맞춰 평행사변형으로 펴기
f=frame(4.75)
d1=np.array([410,-240],np.float32); d1/=np.linalg.norm(d1); p=np.array([-d1[1],d1[0]])*-1  # 바닥 안쪽(왼쪽 위)
p=np.array([-0.505,-0.863],np.float32)
d1=d1-0.12*p; d1/=np.linalg.norm(d1)
A=np.array([470,590],np.float32); B=A+d1*380; D=A+p*250
wood=warp(f,A,B,D,760,500)
mean=wood.reshape(-1,3).mean(0)
target=mean*1.18   # 그늘이라 조금 밝게
wood=flatten(wood,14,target)
wood=np.clip(target+(wood-target)*1.15,0,255)
wood=cv2.resize(seamless(wood),(1024,672),interpolation=cv2.INTER_CUBIC)
# 판 이음선(약 172mm 폭, 1.3m 길이, 엇갈림) + 판마다 약간의 밝기 차
rng=np.random.default_rng(4); rows=5; ph=672//rows
for i in range(rows):
    y0=i*ph; gain=1+rng.uniform(-.07,.07)
    wood[y0:y0+ph]*=gain
    wood[y0:y0+2]*=0.8
    x=int(rng.uniform(0,1024)); wood[y0:y0+ph, max(0,x-1):x+1]*=0.8
wood=np.clip(wood,0,255)
hls=cv2.cvtColor(wood.astype(np.uint8),cv2.COLOR_BGR2HLS).astype(np.float32); hls[...,2]*=0.78
wood=cv2.cvtColor(hls.astype(np.uint8),cv2.COLOR_HLS2BGR).astype(np.float32)
# 판이 X축 방향이 되도록 (d1 방향 = 이미지 가로)
cv2.imwrite(out+'/wood.jpg',wood,[cv2.IMWRITE_JPEG_QUALITY,86])
res['woodMean']=[int(v) for v in target[::-1]]
# 2) 벽지: 54.0s 거실 벽의 평평한 부분 → 밝기 정규화한 결이 있는 흰색
f=frame(54.0)
patch=f[90:330,470:700]  # 콘센트/등 피해 평평한 벽
g=flatten(patch,25,[1,1,1])  # 상대 밝기
g=cv2.cvtColor(np.clip(g*200,0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY).astype(np.float32)/200
detail=(g-1.0)*1.6+1.0
detail=cv2.resize(seamless(np.dstack([detail]*3)),(256,256))
cv2.imwrite(out+'/wall.jpg',np.clip(detail*235,0,255),[cv2.IMWRITE_JPEG_QUALITY,88])
# 3) 문: 44.75s 왼쪽 문짝 가운데
f=frame(44.75)
door=f[120:600,40:250]
gray=cv2.cvtColor(np.clip(door,0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY).astype(np.float32)
gray=gray/cv2.GaussianBlur(gray,(0,0),40)
gray=1+(gray-1)*2.0
dc=np.median(frame(38.5)[400:700,1010:1240].reshape(-1,3),0); dc=dc*(150/dc.mean())
door=np.dstack([gray*dc[0],gray*dc[1],gray*dc[2]])
res['door']='#%02x%02x%02x'%tuple(int(v) for v in dc[::-1])
door=cv2.resize(door,(256,512),interpolation=cv2.INTER_CUBIC)
cv2.imwrite(out+'/door.jpg',door,[cv2.IMWRITE_JPEG_QUALITY,86])
# 4) 색 샘플 (BGR→hex)
def hexc(bgr,gain=1.0):
    b,g,r=[int(np.clip(v*gain,0,255)) for v in bgr]; return '#%02x%02x%02x'%(r,g,b)
def med(f,y0,y1,x0,x1): return np.median(f[y0:y1,x0:x1].reshape(-1,3),0)
def norm_to(bgr,L):  # 밝기를 L(0~255)로 맞춤
    return bgr*(L/max(1,bgr.mean()))
res['wall_living']=hexc(norm_to(med(frame(54.0),90,330,470,700),226))
res['wall_room_mint']=hexc(norm_to(med(frame(46.0),250,500,380,560),218))
res['wall_room2']=hexc(norm_to(med(frame(40.0),300,560,860,1100),224))
res['bath_floor']=hexc(med(frame(16.0),560,700,900,1100))
res['entry_tile']=hexc(med(frame(4.75),600,700,700,860))
res['kitchen_tile']=hexc(norm_to(med(frame(29.0),120,260,40,300),232))
res['door_mean']=hexc(med(frame(44.75),120,600,40,330))
json.dump(res,open(out+'/colors.json','w'),indent=1)
print(res)
