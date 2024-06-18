#include <libpq-fe.h>
#include <string>

extern "C" {
    __declspec(dllexport) PGconn* ConnectDatabase(const char* conninfo) {
        PGconn *conn = PQconnectdb(conninfo);
        if (PQstatus(conn) != CONNECTION_OK) {
            PQfinish(conn);
            return NULL;
        }
        return conn;
    }

    __declspec(dllexport) void DisconnectDatabase(PGconn* conn) {
        PQfinish(conn);
    }

    __declspec(dllexport) PGresult* ExecuteQuery(PGconn* conn, const char* query) {
        PGresult *res = PQexec(conn, query);
        if (PQresultStatus(res) != PGRES_TUPLES_OK) {
            PQclear(res);
            return NULL;
        }
        return res;
    }

    __declspec(dllexport) const char* GetErrorMessage(PGconn* conn) {
        return PQerrorMessage(conn);
    }

    __declspec(dllexport) int GetRowCount(PGresult* res) {
        return PQntuples(res);
    }

    __declspec(dllexport) const char* GetValue(PGresult* res, int row, int col) {
        return PQgetvalue(res, row, col);
    }

    __declspec(dllexport) void ClearResult(PGresult* res) {
        PQclear(res);
    }
}
