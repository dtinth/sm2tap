#!/usr/bin/env python

import os
import sys
import shutil
import plistlib

class Descriptor:

	def __init__(self, name):
		self.name = name
		self.lines = []
	
	def add_line(self, line):
		self.lines.append(line)
	
	def get_text(self):
		return '\n'.join(self.lines)

class StepEvent:

	def __init__(self, event_type, beat, event_flag):
		self.beat = beat
		self.event_type = event_type
		self.event_flag = event_flag
		self.time = None
	
	def set_time(self, time):
		self.time = time

class StepTypeNotFoundException(Exception):
	pass

class NoNotesInTargetException(Exception):
	pass

def stepeventcmp(a, b):
	if abs(a.beat - b.beat) < 1 / 192.0:
		precedence = ['bpm', 'note', 'stop']
		return precedence.index(a.event_type) - precedence.index(b.event_type)
	if a.beat > b.beat:
		return 1
	else:
		return -1

def add_milliseconds(events, zero):
	time = zero
	bpm = 60.0
	last_beat = 0.0
	for event in events:
		time += (event.beat - last_beat) * 60000.0 / bpm
		if event.event_type == 'bpm':
			bpm = event.event_flag
		elif event.event_type == 'stop':
			time += event.event_flag
		event.set_time(time)
		last_beat = event.beat

def tap_note(time, hold_time, flags):
	return {
		'flags': flags,
		'holdTime': hold_time,
		'time': time
	}

def plist_resolve(plist, obj):
	return plist['$objects'][obj['CF$UID']]

class StepToTap:

	def __init__(self, step_file, tap_file):
		self.step_file = step_file
		self.tap_file  = tap_file
	
	def convert(self, step_identifier):
		tap_notes = self.get_tap_notes(step_identifier)
		self.save_tap_notes(tap_notes)
	
	def save_tap_notes(self, tap_notes):
		plist = plistlib.readPlist(self.tap_file)
		objects = plist['$objects']
		root = plist_resolve(plist, plist['$top']['root'])
		list = plist_resolve(plist, root['songTaps'])['NS.objects']
		if len(list) < 1:
			raise NoNotesInTargetException('Step type not found.')
		tap_class = plist_resolve(plist, list[0])['$class']
		list[:] = []
		for tap_note in tap_notes:
			tap_note['$class'] = tap_class
			new_id = len(objects)
			objects.append(tap_note)
			list.append({'CF$UID': new_id})
		shutil.copy2(self.tap_file, self.tap_file + '.bak')
		plistlib.writePlist(plist, self.tap_file)
		
	def get_tap_notes(self, step_identifier):
		if not self.read_steps(step_identifier):
			raise StepTypeNotFoundException('Step type not found.')
		add_milliseconds(self.events, self.song_offset * -1000)
		tap_notes = []
		hold_heads = {}
		for event in self.events:
			if event.event_type == 'note':
				note_type = event.event_flag['note_type']
				column = event.event_flag['column_num']
				column_str = str(column)
				time = int(event.time)
				if note_type == '1':
					tap_notes.append(tap_note(time, 0, column))
				elif note_type == '2':
					hold_heads[column_str] = tap_note(time, 0, column)
					tap_notes.append(hold_heads[column_str])
				elif note_type == '3' and column_str in hold_heads:
					hold_heads[column_str]['holdTime'] = time - hold_heads[column_str]['time']
					hold_heads[column_str]['flags'] |= 16
					del hold_heads[column_str]
		tap_notes.sort(key=lambda x: x['time'])
		return tap_notes

	def get_step_types(self):
		types = []
		descriptors = self.read_descriptors()
		for descriptor in descriptors:
			name = descriptor.name
			text = descriptor.get_text()
			if name == 'NOTES' and text != '':
				notes_info = map(lambda x: x.strip(), text.split(':'))
				identifier = notes_info[0].lower() + '-' + notes_info[2].lower()
				types.append(identifier)
		return types

	def read_steps(self, step_identifier):
		descriptors = self.read_descriptors()
		events = []
		self.song_offset = 0.
		found_step = False
		for descriptor in descriptors:
			name = descriptor.name
			text = descriptor.get_text()
			if text == '':
				continue
			if name == 'BPMS':
				list = text.split(',')
				for item in list:
					item = item.split('=', 1)
					event = StepEvent('bpm', float(item[0]), float(item[1]))
					events.append(event)
			elif name == 'STOPS':
				list = text.split(',')
				for item in list:
					item = item.split('=', 1)
					event = StepEvent('stop', float(item[0]), float(item[1]))
					events.append(event)
			elif name == 'OFFSET':
				self.song_offset = float(text)
			elif name == 'NOTES' and not found_step:
				notes_info = map(lambda x: x.strip(), text.split(':'))
				identifier = notes_info[0].lower() + '-' + notes_info[2].lower()
				if identifier == step_identifier:
					found_step = True
					measures = map(lambda x: x.strip(), notes_info[5].split(','))
					measure_num = 0
					for measure in measures:
						rows = measure.split()
						row_num = 0
						num_rows = len(rows)
						for row in rows:
							time = float(measure_num) + row_num / float(num_rows)
							beat = time * 4
							column_num = 0
							for column in row:
								if column != '0':
									event = StepEvent('note', beat, {
										'column_num': column_num,
										'note_type': column
									})
									events.append(event)
								column_num += 1
							row_num += 1
						measure_num += 1
		if found_step:
			events.sort(stepeventcmp)
			self.events = events
			return True
		return False

	def read_descriptors(self):
		f = open(self.step_file)
		descriptors = []
		current_descriptor = None
		for line in f:
			comment = line.find('//')
			if comment > -1:
				line = line[:comment]
			line = line.strip()
			if current_descriptor == None and len(line) > 0 and line[0] == '#':
				colon = line.find(':', 1)
				if colon > -1:
					current_descriptor = Descriptor(line[1:colon].upper())
					descriptors.append(current_descriptor)
					line = line[colon + 1:]
			if current_descriptor:
				finish = False
				if len(line) > 0 and line[-1] == ';':
					finish = True
					line = line[:-1]
				current_descriptor.add_line(line)
				if finish:
					current_descriptor = None
		f.close()
		return descriptors

if __name__ == '__main__':
	convertor = StepToTap(sys.argv[1], sys.argv[2])
	if len(sys.argv) > 3:
		steptype = sys.argv[3]
	else:
		print "Possible step types:"
		print '\n'.join(map(lambda x: ' - ' + x, convertor.get_step_types()))
		print '\nPlease type in the step type you wish to convert: ',
		steptype = raw_input().strip()
	convertor.convert(steptype)
