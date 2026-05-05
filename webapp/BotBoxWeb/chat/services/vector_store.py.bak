from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import logging

from chat.models import Program, Course, Department

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Singleton VectorStore — uygulama boyunca tek instance,
    ilk search() çağrısında otomatik olarak build edilir.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = None   # build() çağrılana kadar None
        self.data = []
        self._initialized = True

    def build(self):
        """
        Veritabanındaki tüm Program, Course, Department
        kayıtlarını encode edip FAISS index'e ekler.
        """
        texts = []
        self.data = []

        for p in Program.objects.all():
            texts.append(f"{p.name} {p.description or ''}")
            self.data.append(("program", p))

        for c in Course.objects.all():
            texts.append(f"{c.name} {c.code or ''}")
            self.data.append(("course", c))

        for d in Department.objects.all():
            texts.append(f"{d.name} {d.description or ''}")
            self.data.append(("department", d))

        if not texts:
            logger.warning("VectorStore.build(): Veritabanında hiç kayıt yok, index boş kalacak.")
            return

        logger.info(f"VectorStore building with {len(texts)} records...")
        embeddings = self.model.encode(texts, show_progress_bar=False)
        new_index = faiss.IndexFlatL2(384)
        new_index.add(np.array(embeddings).astype("float32"))
        self.index = new_index
        logger.info("VectorStore build complete.")

    def rebuild(self):
        """
        Veriler güncellendiğinde index'i sıfırdan yeniden oluşturur.
        Örnek: yeni scrape sonrası çağır.
        """
        self.index = None
        self.data = []
        self.build()

    def search(self, query: str, k: int = 5) -> list:
        """
        Verilen query'e en yakın k sonucu döner.
        Index boşsa otomatik build eder.
        """
        # İlk aramada otomatik build
        if self.index is None or not self.data:
            logger.info("VectorStore: index boş, otomatik build başlatılıyor...")
            self.build()

        # Build sonrası hâlâ boşsa (DB boş) erken çık
        if not self.data:
            logger.warning("VectorStore.search(): data hâlâ boş, sonuç döndürülemiyor.")
            return []

        query_vec = self.model.encode(query).astype("float32").reshape(1, -1)
        distances, indices = self.index.search(query_vec, k)

        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.data):
                results.append(self.data[idx])

        return results