
from tkinterdnd2 import TkinterDnD

from interface.viewer import VTViewer


# ---------------------------------------------
# APPLICATION
# ---------------------------------------------

if __name__ == "__main__":

    root = TkinterDnD.Tk()

    app = VTViewer(root)

    root.mainloop()
