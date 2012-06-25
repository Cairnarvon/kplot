#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <oct.h>
#include <variables.h>
#include <toplev.h>

#define PLOTTER "kplotter.py"
#define PLOTSRV "http://localhost:8081"

// PKG_ADD: autoload("kplot",            "kplot.oct");
// PKG_ADD: autoload("ktitle",           "kplot.oct");
// PKG_ADD: autoload("kxlabel",          "kplot.oct");
// PKG_ADD: autoload("kylabel",          "kplot.oct");
// PKG_ADD: autoload("kpurge_tmp_files", "kplot.oct");
// PKG_ADD: autoload("kplot_server",     "kplot.oct");

int tmpfile(std::string, bool);
void rmtmp(std::string);
void write_value(std::string, std::string);

DEFUN_DLD(kplot, args, ,
          "Plots data on a graph using an external plotting server.")
{
    int nargin = args.length();
    FILE *pipe;
    int fd;
    RowVector a, b;
    int i;
    char buf[255], *logname;
    struct stat s;

    if (nargin == 1) {
        /* Should be dataset ID. */
        std::string s = args(0).string_value();
        long j;

        j = strtol(s.c_str(), NULL, 10);
        if (j == 0) {
            error("kplot: expected integer.");
            return octave_value_list();
        }

        write_value("dataset", s);
        rmtmp("data");

    } else if (nargin == 2) {
        /* Should be datapoints. */
        if (args(0).rows() != 1 || args(1).rows() != 1) {
            error("kplot: first two arguments must be vectors of reals.");
            return octave_value_list();
        }

        if (args(0).length() != args(1).length()) {
            error("kplot: arguments not of same length.");
            return octave_value_list();
        }

        a = args(0).matrix_value().row(0);
        b = args(1).matrix_value().row(0);

        /* Save dataset to local temporary file. */
        fd = tmpfile("data", true);
        for (i = 0; i < a.length(); ++i) {
            int s;
            s = snprintf(buf, 255, "%10f,%10f\n", a.elem(i), b.elem(i));
            write(fd, buf, s);
        }
        close(fd);

        rmtmp("dataset");

    } else {
        error("kplot: bad input.");
        return octave_value_list();
    }

    octave_add_atexit_function("kpurge_tmp_files");

    /* Check if plot server is set; if not, set it. */
    logname = getenv("LOGNAME");
    if (!logname)
        logname = getlogin();
    if (!logname)
        logname = (char*)"tmp";
    snprintf(buf, 255, "/tmp/oct-%s/server", logname);
    if (access(buf, F_OK) != 0)
        write_value("server", PLOTSRV);

    /* Python script communicates with plotting server and returns graph ID. */
    pipe = popen(PLOTTER, "r");
    fread(buf, sizeof(char), 255, pipe);
    i = atoi(buf);
    pclose(pipe);

    return octave_value(i);            
}

DEFUN_DLD(ktitle, args, ,
          "Sets graph title")
{
    std::string title;
    int fd;

    if (args.length() != 1) {
        error("ktitle: expected exactly one argument.");
        return octave_value_list();
    }

    if (!args(0).is_string()) {
        error("ktitle: expected string argument.");
        return octave_value_list();
    }

    write_value("title", args(0).string_value());
    return octave_value_list();
}

DEFUN_DLD(kxlabel, args, ,
          "Sets X-axis label")
{
    std::string title;
    int fd;

    if (args.length() != 1) {
        error("ktitle: expected exactly one argument.");
        return octave_value_list();
    }

    if (!args(0).is_string()) {
        error("ktitle: expected string argument.");
        return octave_value_list();
    }

    write_value("x-label", args(0).string_value());
    return octave_value_list();
}

DEFUN_DLD(kylabel, args, ,
          "Sets Y-axis label")
{
    std::string title;
    int fd;

    if (args.length() != 1) {
        error("ktitle: expected exactly one argument.");
        return octave_value_list();
    }

    if (!args(0).is_string()) {
        error("ktitle: expected string argument.");
        return octave_value_list();
    }

    write_value("y-label", args(0).string_value());
    return octave_value_list();
}

DEFUN_DLD(kpurge_tmp_files, , ,
          "Clears temporary files associated with kplot")
{
    char cmd[20], *logname;

    logname = getenv("LOGNAME");
    if (!logname)
        logname = getlogin();
    if (!logname)
        logname = (char*)"tmp";
    snprintf(cmd, 20, "rm -r /tmp/oct-%s", logname);
    system(cmd);

    return octave_value_list();
}

DEFUN_DLD(kplot_server, args, ,
          "Sets the plotting server used by the kplot library")
{
    if (args.length() != 1) {
        error("kset_server: expected exactly one argument.");
        return octave_value_list();
    }

    if (!args(0).is_string()) {
        error("kset_server: expected string argument.");
        return octave_value_list();
    }

    write_value("server", args(0).string_value());

    return args(0);
}


int tmpfile(std::string fname, bool trunc)
{
    char dir[14], path[255], *logname;
    int fd;
    unsigned int flags = O_CREAT | O_RDWR;

    /* Create folder, if it doesn't exist. */
    logname = getenv("LOGNAME");
    if (!logname)
        logname = getlogin();
    if (!logname)
        logname = (char*)"tmp";
    snprintf(dir, 14, "/tmp/oct-%s", logname);
    mkdir(dir, S_IRWXU);

    /* Create file, if it doesn't exist. */
    if (trunc)
        flags |= O_TRUNC;
    snprintf(path, 255, "%s/%s", dir, fname.c_str());
    fd = open(path, flags, S_IRWXU);

    return fd;
}

void rmtmp(std::string fname)
{
    char *logname, path[255];

    /* Create folder, if it doesn't exist. */
    logname = getenv("LOGNAME");
    if (!logname)
        logname = getlogin();
    if (!logname)
        logname = (char*)"tmp";
    snprintf(path, 255, "/tmp/oct-%s/%s", logname, fname.c_str());

    remove(path);
}

void write_value(std::string fname, std::string value)
{
    int fd;

    fd = tmpfile(fname, true);
    write(fd, value.c_str(), value.length());
    close(fd);
}
