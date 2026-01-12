import cv2
import numpy as np

class ImagePreprocessor:
    def __init__(self):
        """
        Optimized Image Preprocessor for Drowsiness Detection.
        Prioritizes Low Latency.
        """
        # Sharpening Kernel
        self.sharpen_kernel = np.array([[0, -1, 0], 
                                        [-1, 5, -1], 
                                        [0, -1, 0]])
        
        self.current_mode = "NORMAL"
        
        # Cache for Gamma LUT
        self.cached_gamma = None
        self.cached_lut = None

    def _get_gamma_lut(self, gamma):
        """
        Generate Look-Up Table (LUT) for Dynamic Gamma Correction.
        Uses Caching to avoid recomputing if gamma is unchanged.
        """
        if self.cached_gamma == gamma and self.cached_lut is not None:
            return self.cached_lut

        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255
                          for i in np.arange(0, 256)]).astype("uint8")
        
        self.cached_gamma = gamma
        self.cached_lut = table
        return table

    def analyze_lighting(self, frame):
        """
        Analyze brightness on a small resized frame for speed.
        """
        small_frame = cv2.resize(frame, (64, 64))
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        return brightness

    def apply_gamma_correction(self, image, gamma):
        """Fast Gamma Correction using LUT."""
        lut = self._get_gamma_lut(gamma)
        return cv2.LUT(image, lut)

    def apply_gaussian_blur(self, image):
        """Applies Gaussian Blur for noise reduction."""
        return cv2.GaussianBlur(image, (5, 5), 0)

    def apply_clahe(self, image, clip_limit=2.0):
        """
        Contrast Limited Adaptive Histogram Equalization.
        Expensive operation, use sparingly.
        """
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        return final

    def apply_sharpening(self, image):
        """Applies 2D filter for sharpening."""
        return cv2.filter2D(image, -1, self.sharpen_kernel)

    def process(self, frame):
        """
        Main optimized processing pipeline.
        Returns: processed_frame, mode_name
        """
        brightness = self.analyze_lighting(frame)
        processed = frame

        if brightness < 60: 
            # --- DARK / TUNNEL MODE ---
            self.current_mode = "DARK"
            
            # Gamma + GaussianBlur (Fast)
            processed = self.apply_gamma_correction(processed, gamma=2.0)
            processed = self.apply_gaussian_blur(processed)
            
            # CLAHE: Crucial for dark environments
            processed = self.apply_clahe(processed, clip_limit=3.0)
            
        elif brightness > 180:
            # --- BRIGHT / GLARE MODE ---
            self.current_mode = "BRIGHT"
            
            # Reduce brightness
            processed = self.apply_gamma_correction(processed, gamma=0.6)
            
            processed = self.apply_gaussian_blur(processed)
            processed = self.apply_clahe(processed, clip_limit=1.5)
            
        else:
            # --- NORMAL MODE ---
            self.current_mode = "NORMAL"
            
            # Only light sharpening for normal conditions
            processed = self.apply_sharpening(processed)
            
            return processed, self.current_mode

        # Sharpening for processed images (Dark/Bright)
        processed = self.apply_sharpening(processed)
        return processed, self.current_mode
