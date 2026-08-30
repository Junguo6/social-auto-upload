export namespace engine {
	
	export class AccountPublishResult {
	    platform: string;
	    account: string;
	    success: boolean;
	    errorMsg: string;
	
	    static createFrom(source: any = {}) {
	        return new AccountPublishResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.platform = source["platform"];
	        this.account = source["account"];
	        this.success = source["success"];
	        this.errorMsg = source["errorMsg"];
	    }
	}
	export class AccountStatus {
	    platform: string;
	    account: string;
	    isValid: boolean;
	    msg: string;
	
	    static createFrom(source: any = {}) {
	        return new AccountStatus(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.platform = source["platform"];
	        this.account = source["account"];
	        this.isValid = source["isValid"];
	        this.msg = source["msg"];
	    }
	}
	export class TargetAccount {
	    platform: string;
	    account: string;
	
	    static createFrom(source: any = {}) {
	        return new TargetAccount(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.platform = source["platform"];
	        this.account = source["account"];
	    }
	}
	export class BatchPublishParam {
	    targets: TargetAccount[];
	    concurrency: number;
	    action: string;
	    filePath: string;
	    images: string[];
	    title: string;
	    desc: string;
	    tags: string;
	    thumbnail: string;
	    thumbnailLandscape: string;
	    thumbnailPortrait: string;
	    tid: number;
	    shortTitle: string;
	    category: string;
	    draft: boolean;
	    schedule: string;
	    declaration: string;
	    collection: string;
	    productLink: string;
	    productTitle: string;
	    visibility: string;
	    playlist: string;
	    bgm: string;
	    note: string;
	    notef: string;
	    headless: boolean;
	
	    static createFrom(source: any = {}) {
	        return new BatchPublishParam(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.targets = this.convertValues(source["targets"], TargetAccount);
	        this.concurrency = source["concurrency"];
	        this.action = source["action"];
	        this.filePath = source["filePath"];
	        this.images = source["images"];
	        this.title = source["title"];
	        this.desc = source["desc"];
	        this.tags = source["tags"];
	        this.thumbnail = source["thumbnail"];
	        this.thumbnailLandscape = source["thumbnailLandscape"];
	        this.thumbnailPortrait = source["thumbnailPortrait"];
	        this.tid = source["tid"];
	        this.shortTitle = source["shortTitle"];
	        this.category = source["category"];
	        this.draft = source["draft"];
	        this.schedule = source["schedule"];
	        this.declaration = source["declaration"];
	        this.collection = source["collection"];
	        this.productLink = source["productLink"];
	        this.productTitle = source["productTitle"];
	        this.visibility = source["visibility"];
	        this.playlist = source["playlist"];
	        this.bgm = source["bgm"];
	        this.note = source["note"];
	        this.notef = source["notef"];
	        this.headless = source["headless"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class LoginResult {
	    success: boolean;
	    platform: string;
	    account: string;
	    nickname: string;
	    finderUid: string;
	    msg: string;
	
	    static createFrom(source: any = {}) {
	        return new LoginResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.success = source["success"];
	        this.platform = source["platform"];
	        this.account = source["account"];
	        this.nickname = source["nickname"];
	        this.finderUid = source["finderUid"];
	        this.msg = source["msg"];
	    }
	}
	export class PublishParam {
	    platform: string;
	    action: string;
	    account: string;
	    filePath: string;
	    images: string[];
	    title: string;
	    desc: string;
	    tags: string;
	    thumbnail: string;
	    thumbnailLandscape: string;
	    thumbnailPortrait: string;
	    tid: number;
	    shortTitle: string;
	    category: string;
	    draft: boolean;
	    schedule: string;
	    declaration: string;
	    collection: string;
	    productLink: string;
	    productTitle: string;
	    visibility: string;
	    playlist: string;
	    bgm: string;
	    note: string;
	    notef: string;
	    headless: boolean;
	
	    static createFrom(source: any = {}) {
	        return new PublishParam(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.platform = source["platform"];
	        this.action = source["action"];
	        this.account = source["account"];
	        this.filePath = source["filePath"];
	        this.images = source["images"];
	        this.title = source["title"];
	        this.desc = source["desc"];
	        this.tags = source["tags"];
	        this.thumbnail = source["thumbnail"];
	        this.thumbnailLandscape = source["thumbnailLandscape"];
	        this.thumbnailPortrait = source["thumbnailPortrait"];
	        this.tid = source["tid"];
	        this.shortTitle = source["shortTitle"];
	        this.category = source["category"];
	        this.draft = source["draft"];
	        this.schedule = source["schedule"];
	        this.declaration = source["declaration"];
	        this.collection = source["collection"];
	        this.productLink = source["productLink"];
	        this.productTitle = source["productTitle"];
	        this.visibility = source["visibility"];
	        this.playlist = source["playlist"];
	        this.bgm = source["bgm"];
	        this.note = source["note"];
	        this.notef = source["notef"];
	        this.headless = source["headless"];
	    }
	}

}

