import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)

logger = logging.getLogger("resume_pipeline")
