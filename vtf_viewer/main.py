
import sys

from tkinterdnd2 import TkinterDnD

from interface.viewer import VTViewer

# ---------------------------------------------
# APPLICATION
# ---------------------------------------------

if __name__ == "__main__":

    root = TkinterDnD.Tk()

    filepath = sys.argv[1] if len(sys.argv) > 1 else None
    app = VTViewer(root, filepath=filepath)

    root.mainloop()
