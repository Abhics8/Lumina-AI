from locust import HttpUser, task, between

class LuminaUser(HttpUser):
    wait_time = between(1, 5)

    @task(3)
    def view_homepage(self):
        self.client.get("/")

    @task(1)
    def search_image(self):
        # Simulate an image upload and search query
        with open("demo/test_image.jpg", "rb") as image:
            self.client.post(
                "/api/v1/search",
                files={"file": image},
                data={"text_query": "summer dress", "limit": 5}
            )

    @task(2)
    def health_check(self):
        self.client.get("/api/health")
