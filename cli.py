#!/usr/bin/env python
# -*- coding: utf-8 -*-

import click
import os
import subprocess
import moodle as m


@click.group()
def cli():
    pass


@cli.command("set-text")
@click.argument("course")
@click.argument("section")
@click.option('--filename', default=None, help='Read text from this file.')
@click.option('--config', default="moodle.cfg", help="Configuration file")
@click.option('--pandoc', default=True, help='Run pandoc on file to convert to HTML before pushing to Moodle.')
@click.option('--finalize/--no-finalize', default=False, help='Save changes on Moodle directly.')
def set_text(course, section, filename, config, pandoc=True, finalize=False):
    """
    Set the summary text of a section from a file.
    """
    config = os.path.abspath(config)

    if filename is None:
        filename = section.strip().lower().replace(" ", "-") + ".md"
    if pandoc:
        text = subprocess.check_output(["pandoc",
                                        "--ascii", "--base-header-level=4",
                                        filename]).decode("utf-8")
    s = m.bootstrap()
    s = m.coursef(s, course, editable=True)
    s = m.set_summary(s, section, text, finalize=finalize)
    if s.config["ui"].getboolean("headless") or finalize:
        s.browser.quit()


@cli.command("upload-file")
@click.argument("course")
@click.argument("name")
@click.argument("filename")
@click.option('--config', default="moodle.cfg", help="Configuration file")
@click.option('--finalize/--no-finalize', default=False, help='Save changes on Moodle directly.')
def upload_file(course, name, filename, config, finalize=False):
    """
    Upload a file.
    """
    config = os.path.abspath(config)
    s = m.bootstrap(config)
    s = m.coursef(s, course, editable=True)
    s = m.upload_file(s, name, filename, finalize=finalize)
    if s.config["ui"].getboolean("headless") or finalize:
        s.browser.quit()


@cli.command("list-files")
@click.argument("course")
@click.option('--config', default="moodle.cfg", help="Configuration file")
def list_files(course, config):
    """
    List files of a course.
    """
    config = os.path.abspath(config)
    s = m.bootstrap()
    s = m.coursef(s, course, editable=False)
    file_list = m.file_list(s)
    for fn in file_list:
        print(fn)
    print(s.browser.current_url)
    s.browser.quit()


if __name__ == '__main__':
    cli()
