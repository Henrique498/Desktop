import sys
import requests
import os
import ctypes
import torch
import pygame
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QTextEdit, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from gtts import gTTS
from diffusers import AnimateDiffPipeline, DDIMScheduler, MotionAdapter
from diffusers.utils import export_to_video
from moviepy import ImageClip
from PyQt5.QtGui import QPixmap, QIcon

try:
    
    myappid = 'meu.projeto.livros.ia.v1' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception as e:
    print(f"Erro ao configurar ID do app: {e}")

API_KEY = "AIzaSyAkPO4pP59_pKv0tMcJYWvHt2c020H3yCY"


class VideoAIWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, texto_descricao):
        super().__init__()
        self.descricao = texto_descricao

    def run(self):
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if device == "cuda" else torch.float32
            
            adapter = MotionAdapter.from_pretrained(
                "guoyww/animatediff-motion-adapter-v1-5-2", 
                torch_dtype=dtype
            )
            pipe = AnimateDiffPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5", 
                motion_adapter=adapter, 
                torch_dtype=dtype
            )
            
            pipe.scheduler = DDIMScheduler.from_config(
                pipe.scheduler.config, 
                clip_sample=False, 
                timestep_spacing="linspace", 
                steps_offset=1
            )

            if device == "cuda":
                pipe.enable_model_cpu_offload()
            else:
                pipe.to("cpu")

            foco_visual = self.descricao.split('.')[0]
            prompt_final = f"High quality cinematic book scene, detailed digital art, vibrant colors, motion: {foco_visual[:150]}"
            negative_prompt = "static, blurry, low quality, noisy, distorted, text, watermark, gray static, monochrome"

            output = pipe(
                prompt=prompt_final,
                negative_prompt=negative_prompt,
                num_frames=16,
                num_inference_steps=35,
                guidance_scale=8.5
            )
            
            frames = output.frames[0]
            nome_video = "video_livro_ia.mp4"
            export_to_video(frames, nome_video, fps=10)
            
            self.finished.emit(nome_video)
            
        except Exception as e:
            self.error.emit(str(e))

class GoogleBooksApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Google Books API + AnimateDiff IA")
        self.setWindowIcon(QIcon("icon.jpg"))
        self.setGeometry(200, 200, 900, 600)
        
        
        
        
        
        

        self.books_data = []
        
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"Erro som: {e}")
        
        self.init_ui()
    
 

    def init_ui(self):
        main_layout = QVBoxLayout()
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Digite o nome do livro...")
        self.search_button = QPushButton("Buscar")
        self.clear_button = QPushButton("Limpar")

        self.search_button.setObjectName("btnBuscar")
        self.clear_button.setObjectName("btnLimpar")

        self.search_input.returnPressed.connect(self.search_books)
        self.search_button.clicked.connect(self.search_books)
        self.clear_button.clicked.connect(self.clear_all)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.clear_button)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.show_details)

        content_layout = QHBoxLayout()
        self.image_label = QLabel("Capa")
        self.image_label.setFixedSize(250, 350)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;") 

        text_audio_layout = QVBoxLayout()
        self.details_area = QTextEdit()
        self.details_area.setReadOnly(True)
        
        buttons_layout = QHBoxLayout()
        self.audio_button = QPushButton("Ouvir Áudio")
        self.stop_button = QPushButton("Parar Áudio")
        self.video_button = QPushButton("Gerar Vídeo IA")
        
        self.audio_button.clicked.connect(self.ouvir_descricao)
        self.stop_button.clicked.connect(self.parar_audio)
        self.video_button.clicked.connect(self.gerar_video_ia)

        self.audio_button.setObjectName("btnAudio")
        self.stop_button.setObjectName("btnParar")
        self.video_button.setObjectName("btnVideo")

        buttons_layout.addWidget(self.audio_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.video_button)

        text_audio_layout.addWidget(self.details_area)
        text_audio_layout.addLayout(buttons_layout)
        content_layout.addWidget(self.image_label)
        content_layout.addLayout(text_audio_layout)

        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.results_list)
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        self.versiculo_label = QLabel("“Respondeu Jesus: Eu sou o caminho, a verdade e a vida. Ninguém vem ao Pai, a não ser por mim.” — João 14:6")
        self.versiculo_label.setObjectName("lblVersiculo")
        self.versiculo_label.setAlignment(Qt.AlignCenter) 
        
        main_layout.addWidget(self.versiculo_label) 
       

        self.setLayout(main_layout)

    def gerar_video_ia(self):
        texto_bruto = self.details_area.toPlainText()
        if "Descrição:" in texto_bruto:
            resumo_para_ia = texto_bruto.split("Descrição:")[1].strip()
            self.video_button.setEnabled(False)
            self.video_button.setText("Processando Video...")
            self.worker = VideoAIWorker(resumo_para_ia)
            self.worker.finished.connect(self.on_video_ready)
            self.worker.error.connect(self.on_video_error)
            self.worker.start()
        else:
            QMessageBox.warning(self, "Aviso", "Selecione um livro primeiro!")

    def on_video_ready(self, path):
        self.video_button.setEnabled(True)
        self.video_button.setText("Gerar Vídeo IA")
        if os.path.exists(path):
            os.startfile(path)

    def on_video_error(self, err):
        self.video_button.setEnabled(True)
        self.video_button.setText("Gerar Vídeo IA")
        QMessageBox.critical(self, "Erro", f"Falha na IA: {err}")

    def ouvir_descricao(self):
        texto = self.details_area.toPlainText()
        if "Descrição:" in texto:
            partes = texto.split("Descrição:")
            corpo = partes[1].strip("Descrição:")
            if corpo and corpo != "Sem descrição disponivel.":
                try:
                    texto_final = corpo[:1000]
                    tts = gTTS(text=texto_final, lang='pt')
                    tts.save("temp_audio.mp3")

                    pygame.mixer.music.unload()
                    pygame.mixer.music.load("temp_audio.mp3")
                    pygame.mixer.music.play()
                except Exception as e:
                    QMessageBox.critical(self, "Erro de Áudio", f"Não foi possível gerar o áudio: {e}")
            else:
             QMessageBox.warning(self, "Aviso", "Este livro não possui uma descrição válida para leitura.")
        else:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione um livro com descrição primeiro!")
                
            
        

    def parar_audio(self):
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

    def search_books(self):
        query = self.search_input.text().strip()
        if not query: return
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=15&key={API_KEY}"
            response = requests.get(url, timeout=10).json()
            self.books_data = response.get("items", [])
            self.results_list.clear()
            for book in self.books_data:
                self.results_list.addItem(book["volumeInfo"].get("title", "Sem título"))
        except:
            self.details_area.setText("Erro na conexão.")

    def show_details(self):
        index = self.results_list.currentRow()
        if index < 0: return
        info = self.books_data[index]["volumeInfo"]
        title = info.get("title", "Sem título")
        authors = ", ".join(info.get("authors", ["Desconhecido"]))
        desc = info.get("description", "Sem descrição disponível.")
        self.details_area.setText(f"Título: {title}\nAutores: {authors}\n\nDescrição:\n{desc}")
        
        img_url = info.get("imageLinks", {}).get("thumbnail")
        if img_url:
            img_url = img_url.replace("zoom=1", "zoom=3").replace("http://", "https://")
            try:
                data = requests.get(img_url).content
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                self.image_label.setPixmap(pixmap.scaled(250, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except:
                self.image_label.setText("Erro imagem")

    def clear_all(self):
        self.parar_audio()
        self.search_input.clear()
        self.results_list.clear()
        self.details_area.clear()
        self.image_label.setText("Capa")
        self.image_label.setPixmap(QPixmap())

if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        with open("estilo.qss", "r", encoding="utf-8") as arquivo_qss:
            estilo = arquivo_qss.read()
            app.setStyleSheet(estilo)
    except FileNotFoundError:
        print("Arquivo estilo.qss não encontrado. O app iniciará sem estilos.")
    window = GoogleBooksApp()
    window.setObjectName("GoogleBooksApp")
    window.show()
    sys.exit(app.exec_())