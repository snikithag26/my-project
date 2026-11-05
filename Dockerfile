FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m ml.generate_data && python -m ml.train_asd && python -m ml.train_stress && python -m backend.seed
ENV AUTISPHERE_SECRET=change-me-in-production
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
