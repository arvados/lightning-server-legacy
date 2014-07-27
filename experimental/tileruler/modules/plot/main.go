package plot

const start = `version: 1.0
http://localhost:8000`

func Start() {
	println(start)
	println(ListenAndServe(":8000").Error())
}
