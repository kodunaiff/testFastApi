from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, time

# Настройка базы данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./dog_walking.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Модель данных
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    apartment_number = Column(Integer)
    dog_name = Column(String)
    dog_breed = Column(String)
    walk_time = Column(DateTime)
    walker = Column(String)


Base.metadata.create_all(bind=engine)


# Схема Pydantic для валидации входных данных
class OrderCreate(BaseModel):
    apartment_number: int
    dog_name: str
    dog_breed: str
    walk_time: datetime
    walker: str


# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()


# API методы
@app.post("/orders/")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    # Проверка времени прогулки
    if order.walk_time.time() < time(7, 0) or order.walk_time.time() > time(23, 0):
        raise HTTPException(status_code=400, detail="Walk time must be between 7:00 and 23:00")

    if order.walk_time.minute not in [0, 30]:
        raise HTTPException(status_code=400, detail="Walk time must start at the beginning or middle of an hour")

    # Проверка доступности выгульщика
    existing_order = db.query(Order).filter(
        Order.walk_time == order.walk_time,
        Order.walker == order.walker
    ).first()
    if existing_order:
        raise HTTPException(status_code=400, detail="Walker is not available at this time")

    db_order = Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


@app.get("/orders/{date}")
def get_orders(date: str, db: Session = Depends(get_db)):
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    orders = db.query(Order).filter(Order.walk_time.cast(Date) == date_obj).all()
    return orders


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)