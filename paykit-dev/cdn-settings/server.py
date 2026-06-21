import http.server
import io
import os
import tarfile

PACKAGES_FOLDER = "/home/itsme/programming/paykit-dev/cdn-settings"


class LatestNamedFolderAsTarFile(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PACKAGES_FOLDER, **kwargs)

    def do_GET(self):
        if self.path.endswith(".tar.gz"):
            folder_name = self.path.removeprefix("/").removesuffix(".tar.gz")
            folder_path = os.path.join(PACKAGES_FOLDER, folder_name)
            filename = self.path.split("/")[-1]
            if not os.path.isdir(folder_path):
                self.send_response(404)
                self.end_headers()
                return
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                tar.add(folder_path, arcname=filename)
            buf.seek(0)
            data = buf.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/gzip")
            self.send_header(
                "Content-Disposition", f'attachment; filename="{filename}"'
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().do_GET()


http.server.HTTPServer(("0.0.0.0", 8000), LatestNamedFolderAsTarFile).serve_forever()
