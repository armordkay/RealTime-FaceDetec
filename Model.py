import threading
import cv2
from deepface import DeepFace
import os

face_match = False
face_box = None
lock = threading.Lock() 

def check_face(frame):
    global face_match, face_box, matched_name
    try:
        face_objs = DeepFace.extract_faces(
            img_path=frame,
            detector_backend='opencv',
            enforce_detection=False
        )

        if len(face_objs) > 0 and face_objs[0]['confidence'] > 0:
            obj = face_objs[0]
            facial_area = obj['facial_area']
            
            temp_box = {
                'x': facial_area['x'], 
                'y': facial_area['y'], 
                'w': facial_area['w'], 
                'h': facial_area['h']
            }

            results = DeepFace.find(
                img_path=frame,
                db_path='DB',
                detector_backend='opencv',
                enforce_detection=False,
                model_name="VGG-Face"
            )

            with lock:
                face_box = temp_box 
                if len(results) > 0 and not results[0].empty:
                    face_match = True
                    file_name = os.path.basename(results[0].iloc[0]['identity'])
                    matched_name = os.path.splitext(file_name)[0]
                else:
                    face_match = False
                    matched_name = "Unknown" 
        else:
            with lock:
                face_box = None 
                
    except Exception as e:
        print(f"Error: {e}")

# Check Database
if not os.path.exists("DB"):
    print("DataBase not found!")
    exit()
    
# Load camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

counter = 0

if not cap.isOpened():
    print("Cannot connect to camera. Check the connection or ID again.")
    exit()

while True:
    ret, frame = cap.read()
    if ret:
        current_box = None
        current_match = False
        current_name = "Scanning..."
        if counter % 30 == 0:
            try:
                threading.Thread(target = check_face, args =(frame.copy(),)).start()
            except ValueError:
                pass
        counter += 1
        with lock:
            current_box = face_box
            current_match = face_match
        if current_box is not None:
            x, y, w, h = current_box['x'], current_box['y'], current_box['w'], current_box['h']
            color = (0, 255, 0) if current_match else (0, 0, 255)
        
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            label = matched_name if current_match else "UnKnow"
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        cv2.imshow("Video", frame)
    key = cv2.waitKey(1)
    
    if key == ord('q'):
        break
cap.release()        
cv2.destroyAllWindows()