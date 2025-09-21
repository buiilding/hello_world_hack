import ollama

# For image analysis
response = ollama.chat(
    model='hf.co/mradermacher/UI-Venus-Ground-7B-GGUF:Q8_0',
    messages=[
        {
            'role': 'user',
            'content': 'Outline the position corresponding to the instruction: Firefox Web Browser. The output should be only [x1,y1,x2,y2].',
            'images': ['/media/peter/E/Computer-use/my_own_notebook/tmpkswzyx9o.png']
        }
    ]
)

print(response['message']['content'])