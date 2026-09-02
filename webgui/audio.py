import pygame

pygame.mixer.init()


def play(filename, loop=False):
	try:
		pygame.mixer.music.load(filename)

		if loop:
			pygame.mixer.music.play(-1)
		else:
			pygame.mixer.music.play(0)

	except Exception as e:
		print("Audio error:", e)


def stop():
	pygame.mixer.music.stop()