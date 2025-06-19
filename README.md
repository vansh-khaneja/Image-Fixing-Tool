# Image Processing Application

This repository provides a complete image processing application with two components:

1. A **FastAPI** backend for handling image uploads and processing.
2. A **Next.js** frontend for user interaction.

---

## Backend Setup (FastAPI)

### 1. Navigate to the `server/` directory

```bash
cd server
```

### 2. Create a Virtual Environment (Optional but Recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Server

```bash
python main.py
```

The API will be available at: `http://localhost:8000`

### API Endpoint

**POST /process-image/**

Accepts an uploaded image and returns a processed version.

**Request Format**:

- Method: `POST`
- Content-Type: `multipart/form-data`
- Form field: `file`

---

## Frontend Setup (Next.js)

### 1. Navigate to the `client/` directory

```bash
cd client
```

### 2. Install Dependencies

```bash
npm install
# or
yarn install
```

### 3. Run the Development Server

```bash
npm run dev
# or
yarn dev
```

The frontend will be available at: `http://localhost:3000`

Make sure the backend (FastAPI server) is running on port `8000`.

---

## Integration

The frontend sends a `POST` request to the `/process-image/` endpoint on the backend using `fetch` or Axios. It uploads the image, receives the processed image blob, and displays it directly in the browser.

Ensure CORS is properly configured in the backend to allow requests from the frontend domain.

---

