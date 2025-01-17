# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from pathlib import Path

import pytest
from PIL import Image as PIL_Image


from llama_models.llama3.api.datatypes import *  # noqa: F403
from llama_stack.apis.inference import *  # noqa: F403

from .utils import group_chunks

THIS_DIR = Path(__file__).parent


class TestVisionModelInference:
    @pytest.mark.asyncio
    async def test_vision_chat_completion_non_streaming(
        self, inference_model, inference_stack
    ):
        inference_impl, _ = inference_stack

        provider = inference_impl.routing_table.get_provider_impl(inference_model)
        if provider.__provider_spec__.provider_type not in (
            "meta-reference",
            "remote::together",
            "remote::fireworks",
            "remote::ollama",
        ):
            pytest.skip(
                "Other inference providers don't support vision chat completion() yet"
            )

        images = [
            ImageMedia(image=PIL_Image.open(THIS_DIR / "pasta.jpeg")),
            ImageMedia(
                image=URL(
                    uri="https://www.healthypawspetinsurance.com/Images/V3/DogAndPuppyInsurance/Dog_CTA_Desktop_HeroImage.jpg"
                )
            ),
        ]

        # These are a bit hit-and-miss, need to be careful
        expected_strings_to_check = [
            ["spaghetti"],
            ["puppy"],
        ]
        for image, expected_strings in zip(images, expected_strings_to_check):
            response = await inference_impl.chat_completion(
                model=inference_model,
                messages=[
                    SystemMessage(content="You are a helpful assistant."),
                    UserMessage(
                        content=[image, "Describe this image in two sentences."]
                    ),
                ],
                stream=False,
            )

            assert isinstance(response, ChatCompletionResponse)
            assert response.completion_message.role == "assistant"
            assert isinstance(response.completion_message.content, str)
            for expected_string in expected_strings:
                assert expected_string in response.completion_message.content

    @pytest.mark.asyncio
    async def test_vision_chat_completion_streaming(
        self, inference_model, inference_stack
    ):
        inference_impl, _ = inference_stack

        provider = inference_impl.routing_table.get_provider_impl(inference_model)
        if provider.__provider_spec__.provider_type not in (
            "meta-reference",
            "remote::together",
            "remote::fireworks",
            "remote::ollama",
        ):
            pytest.skip(
                "Other inference providers don't support vision chat completion() yet"
            )

        images = [
            ImageMedia(
                image=URL(
                    uri="https://www.healthypawspetinsurance.com/Images/V3/DogAndPuppyInsurance/Dog_CTA_Desktop_HeroImage.jpg"
                )
            ),
        ]
        expected_strings_to_check = [
            ["puppy"],
        ]
        for image, expected_strings in zip(images, expected_strings_to_check):
            response = [
                r
                async for r in await inference_impl.chat_completion(
                    model=inference_model,
                    messages=[
                        SystemMessage(content="You are a helpful assistant."),
                        UserMessage(
                            content=[image, "Describe this image in two sentences."]
                        ),
                    ],
                    stream=True,
                )
            ]

            assert len(response) > 0
            assert all(
                isinstance(chunk, ChatCompletionResponseStreamChunk)
                for chunk in response
            )
            grouped = group_chunks(response)
            assert len(grouped[ChatCompletionResponseEventType.start]) == 1
            assert len(grouped[ChatCompletionResponseEventType.progress]) > 0
            assert len(grouped[ChatCompletionResponseEventType.complete]) == 1

            content = "".join(
                chunk.event.delta
                for chunk in grouped[ChatCompletionResponseEventType.progress]
            )
            for expected_string in expected_strings:
                assert expected_string in content
