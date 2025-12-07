import torch
print("torch version:", torch.__version__)
print("torch cuda version:", torch.version.cuda)
print("is_available:", torch.cuda.is_available())
print("build:", torch.__config__.show())
