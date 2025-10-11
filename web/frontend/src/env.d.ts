/// <reference types="vite/client" />
/// <reference types="node" />

interface ImportMetaEnv {
	readonly VITE_API_BASE_URL?: string;
	readonly VITE_DEV_SERVER_PORT?: string;
	readonly VITE_DEV_SERVER_HOST?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
