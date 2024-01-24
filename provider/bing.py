import asyncio
import os
import random
from typing import Dict
from typing import List
import httpx
import regex
import requests

BING_URL = os.getenv("BING_URL", "https://www.bing.com")
# Generate random IP between range 13.104.0.0/14
FORWARDED_IP = (
    f"13.{random.randint(104, 107)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
)
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "referrer": "https://www.bing.com/images/create/",
    "origin": "https://www.bing.com",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63",
    "x-forwarded-for": FORWARDED_IP,
}


class ImageGenAsync:

    def __init__(
        self,
        auth_cookie: str = None,
        quiet: bool = False,
        all_cookies: List[Dict] = None,
    ) -> None:
        if auth_cookie is None and not all_cookies:
            raise Exception("No auth cookie provided")
        self.session = httpx.AsyncClient(
            headers=HEADERS,
            trust_env=True,
        )
        if auth_cookie:
            self.session.cookies.update({"_U": auth_cookie})
        if all_cookies:
            for cookie in all_cookies:
                self.session.cookies.update(
                    {cookie["name"]: cookie["value"]},
                )
        self.quiet = quiet

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo) -> None:
        await self.session.aclose()

    async def get_images(self, prompt: str) -> list:
        """
        Fetches image links from Bing
        Parameters:
            prompt: str
        """
        if not self.quiet:
            print("Sending request...")
        url_encoded_prompt = requests.utils.quote(prompt)
        url = f"{BING_URL}/images/create?q={url_encoded_prompt}&rt=3&FORM=GENCRE"
        payload = f"q={url_encoded_prompt}&qs=ds"
        response = await self.session.post(
            url,
            follow_redirects=False,
            data=payload,
        )
        content = response.text
        if "this prompt has been blocked" in content.lower():
            raise Exception(
                "Your prompt has been blocked by Bing. Try to change any bad words and try again.",
            )
        if response.status_code != 302:
            # if rt4 fails, try rt3
            url = f"{BING_URL}/images/create?q={url_encoded_prompt}&rt=4&FORM=GENCRE"
            response = await self.session.post(
                url,
                follow_redirects=False,
                timeout=200,
            )
            if response.status_code != 302:
                print(f"ERROR: {response.text}")
                raise Exception("Redirect failed")
        # Get redirect URL
        redirect_url = response.headers["Location"].replace("&nfy=1", "")
        request_id = redirect_url.split("id=")[-1]
        await self.session.get(f"{BING_URL}{redirect_url}")
        polling_url = f"{BING_URL}/images/create/async/results/{request_id}?q={url_encoded_prompt}"
        if not self.quiet:
            print("Waiting for results...")
        while True:
            if not self.quiet:
                print(".", end="", flush=True)
            # By default, timeout is 300s, change as needed
            response = await self.session.get(polling_url)
            if response.status_code != 200:
                raise Exception("Could not get results")
            content = response.text
            if content and content.find("errorMessage") == -1:
                break

            await asyncio.sleep(1)
            continue
        image_links = regex.findall(r'src="([^"]+)"', content)
        normal_image_links = [link.split("?w=")[0] for link in image_links]
        normal_image_links = list(set(normal_image_links))

        bad_images = [
            "https://r.bing.com/rp/in-2zU3AJUdkgFe7ZKv19yPBHVs.png",
            "https://r.bing.com/rp/TX9QuO3WzcCJz1uaaSwQAz39Kb0.jpg",
        ]
        for im in normal_image_links:
            if im in bad_images:
                raise Exception("Bad images")
        # No images
        if not normal_image_links:
            raise Exception("No images")
        return normal_image_links