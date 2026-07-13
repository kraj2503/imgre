from fastapi import APIRouter
from app.api.endpoints import prompts, images, generation

api_router = APIRouter()
api_router.include_router(generation.router, prefix="/generation", tags=["generation"])
api_router.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
