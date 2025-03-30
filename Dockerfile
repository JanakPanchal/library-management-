FROM python:3.10
WORKDIR /library-management
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5001 5002 5003
CMD ["python", "run_services.py"]
