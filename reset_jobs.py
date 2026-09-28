from config import DATABASE_PATH
from storage import reset_processing_opinions


reset_processing_opinions(
    DATABASE_PATH
)

print("PROCESSING jobs reset to PENDING.")