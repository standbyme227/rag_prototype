from src.config import (
        TEST_VECTORSTORE_DIR,
        V0_VECTORSTORE_DIR,
        V1_VECTORSTORE_DIR
    )

vectorstore_dict = {
    "v0": V0_VECTORSTORE_DIR,
    "v1": V1_VECTORSTORE_DIR,
    # "test": TEST_VECTORSTORE_DIR
}

def get_vectorstore_dir(version):
    return vectorstore_dict[version]