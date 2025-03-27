# __Customer Onboarding CV Architecture__

__App Overview__

``` mermaid
  graph LR;
    A[User] -->|Interacts with| B[Frontend];
    B --> C[I/O Device]
    C --> B
    B --> D[Backend];
    D --> E[AI Model]
    E --> D
    D --> B
```

__Frontend-Backend interaction__
``` mermaid
  graph LR;
    A[Frontend] -->|async POST: image / video file path| B[Backend];
    B -->|async POST: OCR text , OTP Validation, User validation| A;
```

__Backend-AI Model interaction__
``` mermaid
  graph LR;
    A[Backend] -->|Send Image File path| B[CV2 API + easyOCR API];
    A[Backend] -->|Send Video File path| C[CascadeClassifier API + Structural Similarity API];
    B -->|Return OCR | A;
    C --> |OTP Validation using hand signs, User Validation using face similarity | A;

```

<div class="grid cards" markdown>
  - [__<- Table of Content__](index.md)
  - [__App Functionality ->__](functionality.md)
</div>